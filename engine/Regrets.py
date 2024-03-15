from typing import Dict
from engine.SymmetricTree import SymmetricTree
from engine.GameAbstractor import GameAbstractor
import engine.FastCopy as fastcopy
import numpy as np
import pyjson5 as json

#this is required for shared memory accessed between processes
from multiprocessing import shared_memory as mem

#an information set is the lowest level of regrets - representing leaf nodes
class InformationSet():

    #internals
    path:list = None
    symm:SymmetricTree = None
    create:bool = True

    #direct references to our shared numpy array slices (so we don't have to continually locate their paths
    refreg:np.array = None
    refstrat:np.array = None
    refstat:np.array = None

    #initialize a new infoset
    def __init__(self, path:list, symm:SymmetricTree, create:bool = True):

        #save a reference to the symm tree and path
        self.path = path
        self.symm = symm
        self.create = create

        #get shape array reference
        shape = symm.shape()

        #if the last item in our path is an action (not a hand profile)
        #then let's add a fake hand profile to store the infoset
        #this keeping the shape symmetric but allowing non-leaf infosets
        #if path[-1][1] == 1: path += [(shape[2]-1,2)]

        #the # of actions is stored at the leaf level of infosets
        self.num_actions = shape[RegretManager.REGRET_PATH * SymmetricTree.SHAPE_SIZE]

        #if this is a new infoset, set everything up for it
        if self.create:
            if self.symm.get(self.path + RegretManager.PATH_STAT_LOC_READS, default=0, set_default = True) == 0:

                #write default regrets and strategy (using get / default options -> allows us to write
                self.symm.set( self.path + RegretManager.PATH_INFOSET_REGRETS, np.zeros(self.num_actions) )
                self.symm.set( self.path + RegretManager.PATH_INFOSET_STRAT, self.get_default_strategy() )

                #we have now read once and written once
                self.symm.set(self.path + RegretManager.PATH_INFOSET_STAT,[1,1])

        #now, store references back to our internal array slices, so don't have to keep calculating them
        self.refreg = self.symm.get( self.path + RegretManager.PATH_INFOSET_REGRETS, items=self.num_actions )
        self.refstrat = self.symm.get( self.path + RegretManager.PATH_INFOSET_STRAT, items=self.num_actions )
        self.refstat = self.symm.get(self.path + RegretManager.PATH_INFOSET_STAT, items=2)

    #return our reads
    def reads(self):

        #return reads at this path
        #return self.symm.get( self.path + RegretManager.PATH_STAT_LOC_READS,0 )

        #JBC 09/23/21 -> no longer finding the path, use referenced array directly
        return self.refstat[RegretManager.PATH_STAT_LOC_READS[-1][0]]

    #return our writes
    def writes(self):

        #return writes at this path
        #return self.symm.get( self.path + RegretManager.PATH_STAT_LOC_WRITES,0 )

        #JBC 09/23/21 -> no longer finding the path, use referenced array directly
        return self.refstat[RegretManager.PATH_STAT_LOC_WRITES[-1][0]]


    #return our cumulative regrets
    def regrets(self):
        #get regrets
        #regrets = self.symm.get( self.path + RegretManager.PATH_INFOSET_REGRETS,items=self.num_actions)

        #JBC: 09/23/21 -> no longer re-finding the paths of regrets, just saving a reference
        regrets = self.refreg

        #if not initialized, set to zeros -> this will happen when reading from a path that doesn't exist
        #as a "reader" not a trainer
        if type(regrets) == type(None): regrets = np.zeros(self.num_actions)

        #return those raw regrets
        return regrets

    #return our strategy
    def strategy(self):
        #get our strategy
        #strat = self.symm.get( self.path + RegretManager.PATH_INFOSET_STRAT,items=self.num_actions)

        #JBC 09/23/21 -> no long re-finding the paths of strats, just saving a reference
        strat = self.refstrat

        #if not initialized, set to default -> this will happen when reading a path that hasn't been
        #created yet (not trained yet)
        if type(strat) == type(None):  strat = self.get_default_strategy()

        #return a copy of our strategy
        #so that any manipulations by caller do not change the original
        return np.copy(strat)

    #return our actions
    def actions(self):
        return self.num_actions

    #normalize a strategy
    def normalize(self, strategy: np.array) -> np.array:
        #normalize a strategy. If there are no positive regrets,
        #use a uniform random strategy
        if sum(strategy) > 0:
            strategy /= sum(strategy)
        else:
            strategy = self.get_default_strategy()
        return strategy

    #return the default strategy
    def get_default_strategy(self):
        return np.array([1.0 / self.num_actions] * self.num_actions)

    def get_strategy(self, reach_probability: float) -> np.array:

        #do not update strategy if the reach probability is ZERO
        #because the result is not going to change - this can reduce space in the model
        #for those paths we NEVER EVER reach, and can also speed up training by not writing
        #values unnecessarily
        if reach_probability > 0:

            #return regret-matching strategy
            #JBC 10/10/20 -> normalize regrets, but continue to use default
            #until a clear best path emerges (ie sum of regrets is positive)
            #BE SURE TO MAKE A COPY OF REGRETS SO WE DON'T OVERWRITE THEM!!!
            #JBC 09/22/21 -> moved this within the reach probably check since we don't need to get regrets if reach probably is zero
            #JBC 09/22/21 -> removed np.copy() operation within np.maximum call, since np.maximum definition states it makes a copy
            strategy = self.normalize(np.maximum(0, self.regrets()))

            #update strategy sum with new strategy
            #self.symm.set( self.path + RegretManager.PATH_INFOSET_STRAT, reach_probability * strategy, SymmetricTree.MATH_ADD)

            #JBC 09/23/21 -> no longer re-finding the regret array, updating our reference
            self.refstrat += reach_probability * strategy

            #there is one more read
            #self.symm.set( self.path + RegretManager.PATH_STAT_LOC_READS,1,SymmetricTree.MATH_ADD)

            #JBC 09/23/21 -> no longer refinding the stats array, update reference directly
            self.refstat[RegretManager.PATH_STAT_LOC_READS[-1][0]] += 1
            

        #now that we have updated strategy, return normalized strategy sum (i.e. average strategy)
        return self.get_average_strategy()

    def update_regrets(self, counterfactual_values: np.array):

        #there is one more write
        #self.symm.set( self.path + RegretManager.PATH_STAT_LOC_WRITES,1,SymmetricTree.MATH_ADD)

        #JBC 09/23/21 -> no longer finding the stat path, update directly
        self.refstat[RegretManager.PATH_STAT_LOC_WRITES[-1][0]] += 1

        #update regret if we were able to call this value
        #JBC: 9/11/20 - added this to prevent negative regret for actions not taken, does this work?
        #i am wondering if i should actually use the reach probability of the individual regret (strategy) instead
        #if counterfactual_values[i] != 0:

        #update regrets of info set to our regret
        #self.symm.set(self.path + RegretManager.PATH_INFOSET_REGRETS,counterfactual_values,SymmetricTree.MATH_ADD)

        #JBC 09/23/21 -> no longer refinding regrets, using reference
        self.refreg += counterfactual_values

    #return the average strategy (no updating here)
    #if for some reason the strategy is not found we return default
    def get_average_strategy(self) -> np.array:

        #return our strategy, but normalized
        #JBC 09/22/21 -> replace .copy with np.copy()
        #JBC 09/23/21 -> remove np.copy since self.strategy() already calls it
        return self.normalize(self.strategy())

    #return current regrets
    def get_regrets(self) -> np.array:

        #return our regrets, but normalized
        #BE SURE TO MAKE A COPY SO WE DON'T OVERWRITE CUMULATIVE REGRETS
        #JBC 09/22/21 -> replace .copy with np.copy()
        return self.normalize(np.copy(self.regrets()))

#strategy manager abstracts the logic for tracking strategy at each iteration of CFR
class StrategyManager():

    #initialize the strategy manager for this strategy
    def __init__(self, strategy: np.array,action_sets: int):
        super().__init__()
        self.strategy = strategy
        self.counterfactual_values = np.zeros(action_sets)

    #normalize a strategy
    def normalize(self, strategy: np.array) -> np.array:
        #normalize a strategy. If there are no positive regrets,
        #use a uniform random strategy
        if sum(strategy) > 0:
            strategy /= sum(strategy)
        else:
            strategy = np.array([1.0 / len(strategy)] * len(strategy))
        return strategy

    #record a counterfactual value for a given action (index)
    def set_counterfactual_value(self,action: int, value: float):
        self.counterfactual_values[action] = value

    #get active regret - that is for this exact counterfactual strategy
    def get_active_strategy(self):

        #our counterfactual values can be negative, adjust for that
        strategy = self.counterfactual_values.copy()
        strategy += max(abs(strategy))

        #now normalize them
        stratsum = sum(strategy)
        if stratsum == 0:
            strategy[:] = 1 / len(strategy)
        else:
            strategy /= stratsum

        #2021-08-27 - renormalize again by the current strategy
        #this will remove strategies that can't be called (zeroed out by iteration)
        strategy *= self.strategy
        strategy /= sum(strategy)

        #return that strategy
        return strategy

    #calculate regret given reget values and strategies
    def get_regret(self):
        #dot multiplies each counterfactual value by its corresponding strategy
        #then sums those values to get a total

        #JBC: 9/13/21 -> added normalize here because the regret was being weighted against actions not taken
        #for example, in "COMMODITY" game: symm strategy = [Buy:25%,Sell:50%,Hold:25%], but Buy and Hold are not valid
        #so the strategy looks like [0,.5,0] -> selling returns 7K regret, but weighted that returns [0,3.5k,0] so
        #the likelyhood of taking this path is reduced for prior steps in our iterate method

        return self.counterfactual_values.dot(self.normalize(self.strategy))

    #update info set regrets given reach probability
    def update_regrets(self, info_set: InformationSet, reach_probability: float):
        #JBC 10/6/20 -> moved this reach_probability check from infset update_regrets to here
        #because we are no longer passing reach_probability to infoset, and instead are apply the calc here

        #if our reach probability is ZERO, then we don't need to write regrets
        #because the result is not going to change - this can reduce space in the model
        #for those paths we NEVER EVER reach, and can also speed up training by not writing
        #values unnecessarily
        if reach_probability == 0: return

        #get our regret
        current_regret = self.get_regret()

        #JBC 10/6/20 -> calculate counterfactual values based on reach probability and current strategy
        #which will prevent paths we did not take from attributing value (negative or positive)
        #adjusted_regrets = self.strategy * reach_probability * (self.counterfactual_values - current_regret)

        #JBC 10/9/20 -> back to old way for testing
        #note the additional np where function prevents us from adjusting regrets that were not actually triggered
        #adjusted_regrets = reach_probability * (self.counterfactual_values - current_regret) * np.where(self.strategy > 0, 1, self.strategy)

        #JBC 10/9/20 -> for below we are not normalizing to 1 - this will make the adjustments to regret smaller
        #adjusted_regrets = reach_probability * (self.counterfactual_values - current_regret)

        #JBC 11/9/20 -> do not adjust strategies that were not used (strategy is ZERO)
        #this concept works fine as long as we are not normalizing remaining startegies
        #which tilts our training too quickly to the paths that are available to take
        adjusted_regrets = reach_probability * (self.counterfactual_values - current_regret) * np.where(self.strategy > 0, 1, self.strategy)

        #update infoset with regret
        info_set.update_regrets(adjusted_regrets)

#regret manager abstracts the logic for calculating and tracking counterfactual regrets, and strategy(probabilities)
#so we can test between different games without needing to abstract our CFR agent
class RegretManager():

    # internal references
    game_abstractor = None
    symmtree_shape = None
    symm_tree = None
    on_disk = True

    # all regret managers are stored in shared memory automatically now
    # this memory may be on disk as virtual memory or in-memory
    # because we can have multiple regret managers loaded at the same time
    # we need a name for each namesapce (generally this should relate to the game loaded
    # default is the generic legacy name "regrets_tree"
    namespace = "regrets_tree"

    # we no longer have a hard-coded symmtree shape
    # but there are several paths that are referenced throughout
    # the infromationset process - so when we get the path from
    # the game abstractor, we are going to get those paths as well
    # and set them here for reference within the infoset process
    # these are placeholders
    INFOSET_PATH = 0
    REGRET_PATH = 0
    STRAT_PATH = 0
    STAT_PATH = 0

    # specific static definition locations -> these don't change regardless of overall symmtree shape
    REGRET_LOC = 0
    STRAT_LOC = 1
    STAT_LOC = 2

    # definitions of statistic values -> these don't change regardless of overall symmtree shape
    STAT_LOC_READS = 0
    STAT_LOC_WRITES = 1

    # predefine some common paths for statistics
    PATH_STAT_LOC_READS = []
    PATH_STAT_LOC_WRITES = []

    # predefine some common paths for regrets and strategies
    PATH_INFOSET_REGRETS = []
    PATH_INFOSET_STRAT = []
    PATH_INFOSET_STAT = [(STAT_LOC, INFOSET_PATH), (0, STAT_PATH)]

    # our settings
    settings = {}

    # initialize the regret manager
    def __init__(self, namespace="regrets_tree"):
        super().__init__()

        # save our namesapce
        self.namesapce = namespace

        # for evaluation
        self.added_regrets = 0

        # for testing, we track training iterations on the regret manager
        self.training_iteration = 1

        # initialize shared identity logic for regret locks
        self.shared_identity = None

    #has our symm tree been initialized (loaded or opened) already either on disk or otherwise)
    def initialized(self):
        return (self.symm_tree != None)

    #return the default strategy
    def get_default_strategy(self):
        #the # of actions is stored at the leaf level of infosets
        num_actions = self.symm_tree.shape()[RegretManager.REGRET_PATH * SymmetricTree.SHAPE_SIZE]
        return np.array([1.0 / num_actions] * num_actions)

    # get an information set given the game state
    def get_information_set(self, game_state, player, save_set=True, regret_path=None) -> InformationSet:
        # get regret path
        # for testing - add training iteratoin to regret path to keep each regret unique
        if regret_path == None:
            regret_path = self.game_abstractor.gen_regret_path(game_state, player)

        #return an infoset reference for this path
        return InformationSet(path=regret_path, symm=self.symm_tree, create=save_set)

    #get the training of a regret node
    def eval_training(self, quick=False):
        #the total number of leaf nodes is actually stored as the last value of the array (where we track size / shape)
        (_,_,_,regret_nodes) = self.symm_tree.levelinfo(RegretManager.REGRET_PATH)
        (strategy_size,_,_,strategy_nodes) = self.symm_tree.levelinfo(RegretManager.STRAT_PATH)
        trained_nodes = 0

        #if we have time, calculate trained nodes:
        if not quick:
            #reshape the array as 2d
            view = self.symm_tree._arrays[RegretManager.STRAT_PATH][0:strategy_nodes * strategy_size].reshape(-1,strategy_size)

            #trained nodes are those where at least 1 action has pulled away from average strategy
            #if all strategies are closly aligned, the node is really not trained yet
            trained_nodes = np.count_nonzero(np.max(view,axis=1) - np.min(view,axis=1) > 0.01)

        #this needs to be reevaluated
        #for now just return the # of defined information set arrays div 3  (since there are 3 for each infoset)
        return regret_nodes, strategy_nodes, trained_nodes

    #configure regret manager for a specific game
    #this will reset everything on the regret manager and sets it up
    #based on settings in the given game config file
    def configure(self, filename, games, settings=None ):

        #load information about this regret manager
        #this will tell us what games it can play, etc
        if settings == None:
            with open("{}/settings.json".format(filename)) as jfile:
                settings = json.load(jfile)

        #make our own copy of settings
        self.settings = fastcopy.deepcopy(settings)

        #save our filename
        self.filename = filename
        self.on_disk = self.settings.get("ondisk",True)

        #get a namespace (specificlaly for when loading into memory)
        self.namespace = self.settings.get("namespace",self.namespace)

        #the settings decide what game we can play
        game = self.settings["game"]

        #they also decide if we store our symmetric tree in memory 
        #or if we open it on disk (in case its quite large)

        #settings contains a game name, we are passed all games
        #and we load the appropriate abstractor given the game
        game_abstractor = games[game].abstractor
        self.game_abstractor = game_abstractor

        #configure the game abstractor using the settings as well
        #since some games and game abstractors use customizable settings in the settings file
        game_abstractor.configure(self.settings)

        # previously we allocated or attached to symmetry tree right here
        # now we are going to just set its value to None
        self.symmtree_shape = game_abstractor.symmtree_shape()

        ##### NOTICE THAT BELOW WE ARE SETTING *GLOBAL* CLASS VALUES NOT INSTANCE VALUES ######

        # if no infoset paths are provided, assume the last 4 paths in the tree
        if game_abstractor.infoset_paths() == None:

            #we can just assume the last 4 paths are for our infosets (that's usually true)            
            RegretManager.INFOSET_PATH = len(self.symmtree_shape)-4
            RegretManager.REGRET_PATH = len(self.symmtree_shape)-3
            RegretManager.STRAT_PATH = len(self.symmtree_shape)-2
            RegretManager.STAT_PATH = len(self.symmtree_shape)-1

        else:

            # now we need the infoset related paths
            (RegretManager.INFOSET_PATH, RegretManager.REGRET_PATH, RegretManager.STRAT_PATH, RegretManager.STAT_PATH) = game_abstractor.infoset_paths()

        # setup our actual paths now -> for stats
        RegretManager.PATH_STAT_LOC_READS = [(RegretManager.STAT_LOC, RegretManager.INFOSET_PATH), (RegretManager.STAT_LOC_READS, RegretManager.STAT_PATH)]
        RegretManager.PATH_STAT_LOC_WRITES = [(RegretManager.STAT_LOC, RegretManager.INFOSET_PATH), (RegretManager.STAT_LOC_WRITES, RegretManager.STAT_PATH)]

        # setup our actual paths now -> for infosets
        RegretManager.PATH_INFOSET_REGRETS = [(RegretManager.REGRET_LOC, RegretManager.INFOSET_PATH), (0, RegretManager.REGRET_PATH)]
        RegretManager.PATH_INFOSET_STRAT = [(RegretManager.STRAT_LOC, RegretManager.INFOSET_PATH), (0, RegretManager.STRAT_PATH)]
        RegretManager.PATH_INFOSET_STAT = [(RegretManager.STAT_LOC, RegretManager.INFOSET_PATH), (0, RegretManager.STAT_PATH)]

    #create regrets on disk
    def create(self, filename = None):

        #create a new symmetric tree on disk if file provided
        if filename != None:
            self.symm_tree = SymmetricTree(shape=self.symmtree_shape,filename="{}/regrets".format(filename), ondisk=True)
            self.on_disk = True
            self.shared_memory = False
            self.shared_space = filename
        else:
            self.symm_tree = SymmetricTree(shape=self.symmtree_shape,namespace=self.namespace)
            self.on_disk = False
            self.shared_memory = True
            self.shared_space = self.namesapce

    #open regrets on disk
    def open(self, filename):

        #create a new symmetric tree on disk
        self.symm_tree = SymmetricTree(filename="{}/regrets".format(filename), ondisk=True)
        self.shared_space = filename

        #we are on disk
        self.on_disk = True
        self.shared_memory = False

        #update settings dictionary as well (to match what we just forced, in case those tsettings are used elsewhere)
        self.settings["ondisk"] = True


    #save regrets to a file
    def save(self, filename, verbose=False):

        #save our symmetric tree
        self.symm_tree.save(filename="{}/regrets".format(filename), verbose=verbose)

    #attach regrets to memory
    def attach(self):

        #create a new symmetric tree
        self.symm_tree = SymmetricTree(namespace=self.namespace)

        #we are lodaed to shared memory
        self.shared_memory = True
        self.on_disk = False
        self.shared_space = self.namespace

        #update settings dictionary as well (to match what we just forced, in case those tsettings are used elsewhere)
        self.settings["ondisk"] = False

    # load all regrets at once from disk
    def load(self, filename):

        # create a new symmetric tree
        self.symm_tree = SymmetricTree(shape=self.symmtree_shape, namespace=self.namespace)

        # we are lodaed to shared memory
        self.shared_memory = True
        self.on_disk = False
        self.shared_space = self.namespace

        #update settings dictionary as well (to match what we just forced, in case those tsettings are used elsewhere)
        self.settings["ondisk"] = False

        # load our symmetric tree
        self.symm_tree.load(filename="{}/regrets".format(filename), verbose=True)

    #initialize regretman -> will load/open/attach as appropriate
    def initialize(self, reopen=False):

        #if we are initialized, or reopening
        if not self.initialized() or reopen:

            #should we open on disk, attach to memory, or load from disk into memory
            if self.on_disk: 
                
                #open on disk
                self.open(self.filename)

            else:

                #try to attach to the namespace, otherwise load
                try:
                    print("attaching to namespace {}".format(self.namespace))
                    self.attach()
                except:
                    print("loading namespace {}".format(self.namespace))
                    self.load(self.filename)