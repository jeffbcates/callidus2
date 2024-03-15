#for debuggin
import cProfile
import pstats

import console
import random
import numpy as np
import time
import multiprocessing
import games
from games import Game
import engine.FastCopy as fastcopy
from engine.Signaling import Signaling
from engine.Callidus import Callidus
from engine.Regrets import RegretManager
from engine.Regrets import StrategyManager
from engine.Regrets import InformationSet
from engine.Trainee import Trainee
from engine.Traceable import Traceable
from engine.GameStateAbstractor import GameStateAbstractor

#some training signals
SIGNAL_EPOCH_READY = 0
SIGNAL_SLAVE_READY = 0
SIGNAL_EPOCH_START = 1
SIGNAL_EPOCH_STOP = 2
SIGNAL_TRAINING_STOP = 3

#our trainer class
class Trainer (Traceable):

    #our game reference
    game:Game = None
    regretMan:RegretManager = None
    trainee = None
    argmax = True
    traceIdentity = 0
    utilizeActiveStrategy = False
    traceDepth = 0

    #our game state analyzer
    stateAbstractor:GameStateAbstractor = GameStateAbstractor()

    #the identity of this specific trainer instance (written to trace log)
    identity = 0

    #internally track our epoch, step, and minutes
    epoch = 0
    step = 0

    #we do not continue to train strategies with an average strategy below this
    strategyThreshold:float = 0.01 

    #iterate through the action tree
    def iterate(self, gameState:dict, actions:dict, reachProbability:float, depth:int = 0):

        #if the round is finished
        #get the utility and return
        if self.game.roundFinished(gameState):
            #return utility of this path
            return self.game.utility(gameState,self.trainee), gameState

        #if the reach probability is zero, the utility is zero
        if reachProbability == 0:
            return 0, gameState

        #flatten our actions using the game abstractor
        actions = self.game.abstractor.flatten_actions(actions)

        #create an empty action state array that tracks the states
        #that result from the different action paths we take
        actionStates = [None for i in range(len(actions))]

        #get the current information set for given game state
        infoSet = self.regretMan.get_information_set(gameState,self.trainee)

        #log this game state to game state abstractor
        #self.stateAbstractor.analyzeState(gameState)

        #get our current strategy from the information set
        #this will update the strategy sum and then return the newly updated average strategy
        strategy = infoSet.get_strategy(reachProbability)

        #create a strategy manager for that strategy, to help compute regrets, etc
        #the strategy manager needs to know the # of action sets in order to compute regrets
        stratMan = StrategyManager(np.copy(strategy), self.game.abstractor.action_sets())

        #zero out strategies that are not possible
        for c in range(len(actions)):
            if not self.game.validAction(gameState, actions[c]):
                strategy[c] = 0

        #recompute strategy based on valid actions
        if sum(strategy) != 0: strategy /= sum(strategy)
        else:
            bestActionIndex = 0


        #for each of the possible actions
        for c in range(len(actions)):
        
            #if this is a valid action we should iterate it
            #skip node if very low reach probability
            if strategy[c] > self.strategyThreshold:

                #compute new reach probability after this action
                newReachProbability = reachProbability * strategy[c]

                #make a copy of the game state
                #so we don't mangle it with our testing
                workingState = fastcopy.deepcopy(gameState)
        
                #set the trainee action to this action
                self.trainee.setNextAction(actions[c])

                #step the game with this working state and record the new state
                #here we step until our players turn again
                workingState = self.game.stepBackToPlayer(workingState,self.trainee)
            
                #get valid possible actions from game
                validActions = self.game.abstractor.valid_actions(workingState)

                #get all possible next actions from state
                #and call iterate with those            
                utility, actionState = self.iterate(workingState, validActions, newReachProbability, depth+1)

                #save action state
                #JBC: 9/13/21 -> instead of returning final action state, return the current working state
                #this will improve tracing, but also mean each step is iterated multiple times 
                #(because the outer training loop will call each step (which iterates that step and all further steps)

                #actionStates[c] = actionState
                actionStates[c] = workingState

                #record utility in strategy manager
                #JBC: 11/9/20 -> utility should NOT be multiplied by -1 because higher is better
                stratMan.set_counterfactual_value(c, utility)

            else:

                #JBC: 10/6/20 -> zero out the strategy of any actions we did not take
                #what happens when strategy is zero
                utility = 0
                strategy[c] = 0
                stratMan.strategy[c] = 0

            #JBC: 10/6/20 -> normalize this current strategy (since we previously zeroed out some of the strategies)
            #and update it in strategy manager (this will prevent us from assigning a false value to paths we did not take)
        
            #JBC: 10/9/20 -> do not normalize strategy since the zeroed out strategies could be selected at a later date)
            #strategy = info_set.normalize(strategy)

            #JBC: 11/9/20 -> clear our zeroed strategies so they aren't negatively impacted but DO NOT NORMALIZE
            #stratMan.strategy = strategy

        #JBC: 09/11/21 -> moved this outside of the action loop since it should update only once for all strategies
        #not update 3 times, once for each strategy
        #let the strat manager update the info set based on current reach probability
        stratMan.update_regrets( infoSet , reachProbability)

        #now that we have looped through all actions - get the average strategy from the infoset / or from the current iteration
        #we have a setting that lets us decide if we should use the average strategy or active strategy
        if self.utilizeActiveStrategy:
            strategy = stratMan.get_active_strategy()
        else:
            strategy = infoSet.get_average_strategy()

        #recalculate strategy against current (stratMan) strategy, to remove invalid actions
        #then renormalize them
        strategy *= np.where(stratMan.strategy > 0, 1, stratMan.strategy)
        if sum(strategy) != 0: strategy /= sum(strategy)
        
        #use argmax to pick an action from our strategy
        #bestActionIndex = np.argmax(strategy)

        #pick a random action from the strategy
        #but weight based on the strategy
        bestActionIndex = random.choices(range(len(strategy)), weights=strategy, k=1)[0]

        #set the trainee action to the best action we've found
        self.trainee.setNextAction(actions[bestActionIndex])

        #JBC 10/6/20 -> big change, we should be returning the utility of this entire node-set not the best action found
        #JBC 11/9/20 -> should be returning the strategy managers calculated total regret (not utility becuase that's declared in a loop above)
        #JBC 9/13/21 -> returning actual strategy and original strategy for tracing
        #JBC 9/22/21 -> removed strategy/original as it was doubling the time to complete iterations (don't need it that bad!)
        return stratMan.get_regret(), actionStates[bestActionIndex]

    #configure our trainer based on given settings
    def configure(self, settings):

        #other settings also come from the settings file (stored within game regrets folder)
        self.strategyThreshold = settings.get("strategyThreshold",0.01)

        #do we use an activey or average strategy while training?
        #during poker training i always used average strategy, but testing out commodity training with active
        self.utilizeActiveStrategy = settings.get("utilizeActiveStrategy",False)

        #all things about tracing
        seed = settings.get("randomSeed",0)
        self.argmax = settings.get("argmax",True)
        self.tracing = settings.get("trace",False)
        self.profile = settings.get("profile",False)
        self.traceDepth = settings.get("traceDepth",0) - 1
        self.traceIdentity = settings.get("traceCore",0) - 1

        #if trace depth is -1 that means we are tracing all depths
        if self.traceDepth == -1: self.traceDepth = 1000

        #seed the random number generator if a seed was provided
        if seed != 0: random.seed(seed)

    #iterate the game
    def traingame(self, game, gameState, signaling, step, default_strategy):

        #step through the game until it completes
        while not game.finished(gameState):

            #step until its the players turn
            #but do not execute the players turn - we will do that
            gameState = game.stepToPlayer(gameState, self.trainee)

            #get valid actions for current state
            actions = self.game.abstractor.valid_actions(gameState)

            #iterate through the game
            #and choose the best action for the current state
            #returning the state AFTER THAT ACTION
            utility, gameState = self.iterate(gameState,actions,1)

            #if strategy is empty, it's because the game is over, just return default strategy
            #JBC 9/22/21 -> for testing, remove any reference to strategy here
            strategy = default_strategy #regretman.get_default_strategy()
            activeStrategy = default_strategy #regretman.get_default_strategy()

            #calculate our signal as step * rounds + round
            signaling.SetSignal( ( step-1) * game.rounds + game.round(gameState))

            #trace
            self.trace (
                self.identity,
                self.epoch,
                step, #trace our specific step (not overall epoch step which means nothing in a trace)
                gameState.get("round",None),
                gameState.get("step",None),
                self.game.abstractor.action_name(self.trainee.nextAction),
                utility,
                *strategy,
                *activeStrategy
            )



        #return the game state
        return gameState

    #trainsteps - child process to the train function
    #this allows the train function to kick off multiple processes during an epoch
    #training on different "steps" of the epoch (although the steps happen simultaneously)
    #identity -> the identity of this trainer in the buffer (passed by name)
    def trainsteps(self, identity, buffer, steps, regretfile, settings:{}):

        #configure based on given settings
        self.configure(settings)

        #save our identity for tracing
        self.identity = identity

        #if the trace core is not our identity, we are not responsible for tracing, some other slave is
        if self.traceIdentity != identity and self.traceIdentity != -1: self.tracing = False

        #create a new signaling object as a slave
        signaling = Signaling(name=buffer,identity=identity)

        #are we single threaded?
        singular = (signaling.GetTotal() == 1)

        #create a new regret manager and configure with the passed settings (in case anything was modified from on disk using set operations)
        regretman = RegretManager()
        regretman.configure(regretfile, games.registeredGames, settings=settings)

        #initialize the regretman using those settings configured
        regretman.initialize()

        #open our trace file
        if self.tracing: self.openTrace(regretfile,"trace.txt")

        #get a game reference from the regret manager
        game = games.registeredGames[regretman.settings["game"]]

        #open the correct game for that regret manager
        self.regretMan = regretman
        self.game = game

        #create players - they will all be callidus for our purpose
        #then configure them all using the same regret manager
        players = [Trainee("p0",game)] + [Callidus("p{}".format(p),game) for p in range(1,game.seats)]
        [c.configure(regretman, self.argmax) for c in players]

        #the first player is our trainee
        self.trainee = players[0]

        #get a starting game state given our players
        gameState = game.setup(players)

        #testing - write out some information about training before we start
        #console.writeline("Slave {} Ready: TraceID = {} Tracing = {}".format(identity, self.traceIdentity, self.tracing))

        #continue to process until we receive the stop incom
        signal = SIGNAL_EPOCH_READY
        done = False
        while not done:

            #get the siginal
            signal = signaling.GetSignal()

            #if the end of game signal was received, we are done
            if signal == SIGNAL_TRAINING_STOP: done = True

            #if the end of epoch signal was reeived
            if signal == SIGNAL_EPOCH_STOP:

                #reset our step
                signaling.SetSignal(SIGNAL_SLAVE_READY)

                #wait while our signal value is 2
                if not singular: signaling.WaitWhileSignal(SIGNAL_EPOCH_STOP)

            #if the start of epoch signal was received
            if signal == SIGNAL_EPOCH_START:
                #acknowledge epoch start signal
                #print("SLAVE {}: received epoch start signal - {}".format(identity,steps))

                #continue for our specified number of work units
                for s in range(1,steps+1):

                    #update our epoch and step per signaling registers from master
                    self.epoch = signaling.GetRegister(0)
                    self.step = signaling.GetRegister(1)

                    #reseting the game will shift player positions as well
                    gameState = self.game.reset(gameState)

                    #if we are running in singular mode, go ahead and run a profile too
                    if singular and self.profile:

                        #let them know what we are doing
                        console.writeline("Profiling on 1 Core!")

                        #run the game within a profile
                        with cProfile.Profile() as profile:

                            #step 1 game withi profile
                            gameState = self.traingame(game,gameState,signaling,s, regretman.get_default_strategy())

                            #print out stats
                            ps = pstats.Stats(profile)
                            ps.sort_stats('cumtime','tottime')
                            ps.print_stats()
                            console.writeline("")
                            console.prompt("Hit enter to continue")
                            console.writelin("")

                    else:

                        #just run the game
                        gameState = self.traingame(game,gameState,signaling,s,regretman.get_default_strategy())
                        
                #communicate that we are done with all work units
                signaling.SetSignal(steps * game.rounds)

                #wait until signal of completion was received by master
                if singular: done = True
                else: signaling.WaitForSignal(SIGNAL_EPOCH_STOP)

            #if we received a wait for start signal
            if signal == SIGNAL_EPOCH_READY:

                #wait until we get a new signal (besides zero - which is to wait)
                if not singular: signaling.WaitWhileSignal(SIGNAL_EPOCH_READY)

        #end of slave -> here we can do shutdown operations

    #train a regret tree on a game
    def train(self, game:Game, regretman:RegretManager, settings:{}):

        #get the regret file from the path stored in settings
        regretfile = regretman.filename

        #these values are only used within this function
        epochSize = settings.get("epochSteps",1000)
        epochs = settings.get("epochs",100)
        minutes = settings.get("minutes",0)
        resetAfter = settings.get("resetAfter",0)
        cores = settings.get("cores",0)
        actionsets = len(settings.get("actions",[1]))

        #configure our trainer with all other settings
        self.configure(settings)

        #reset every (default to an epoch that won't happen)
        resetEvery = settings.get("resetEvery",0)
        resetEvery = epochs + 1 if resetEvery == 0 else resetEvery

        #if cores is zero, we use all cores
        if cores == 0: cores = multiprocessing.cpu_count()

        #create our signaling object
        signaling = Signaling(slaves=cores, registers=2)

        #start all our training processes (if we have more than 1)
        processes = []
        workunits = int ( epochSize / cores)
        console.writeline("starting processes")
        if cores > 1: 
            for c in range(0,cores):
                console.progress("Registering Cores",c,cores)
                p = multiprocessing.Process(target=self.trainsteps, args=(c,signaling.Name(),workunits,regretfile, settings,))
                p.start()
                processes.append(p)
        else:
            console.writeline("Training on 1 core - bypassing multi-core processing")

        #open our trace file and write out the header
        #NOTE: we must do this after replicating our process because we can't pickle a file buffer object
        self.openTrace(regretfile,"trace.txt")
        self.traceHeader("core","epoch","step","round","gamestep","action","utility",*game.abstractor.game_actions().keys(),*["Active " + k for k in game.abstractor.game_actions().keys()])

        #now train the players on this game
        epoch = 1
        while epoch <= epochs:

            #signal the start of the next epoch by passing 1
            signaling.SetRegister(0,epoch)
            signaling.SetSignal(SIGNAL_EPOCH_START)

            #now wait for each process to finish
            running = cores
            while running > 0:

                #the step is actually the sum of all signals from slaves
                #and we know we are running when not all slaves have signal 5
                active = signaling.GetActive()
                step = signaling.GetSignal()
                running = active - signaling.CountSignal(workunits * game.rounds)
                signaling.SetRegister(1,step)

                #display progress to the console
                suffix = "Step {} - {:.0f} % Active".format(step, active / cores * 100)
                console.progress("Epoch {}".format(epoch),step, epochSize * game.rounds ,suffix)

                #if we are training with 1 core only, then we don't sleep, we just call "trainsteps" on ourselves
                #we would only train on 1 core if we are actually debugging, otherwise its always better to train on many cores
                if cores == 1:
                    self.trainsteps(0,signaling.Name(),workunits,regretfile, settings)
                else:
                    #we still have something going on
                    time.sleep(1)

            #after the first epoch, analyze the game state gathered in game state abstractor
            #if epoch == 1: self.stateAbstractor.abstractStates()

            #if we want to reset after this epoch, or reset every N epochs, do so
            if epoch == resetAfter or ( epoch % resetEvery == 0):
                console.writeline("")
                console.writeline("MASTER: Reseting Regrets...")
                regretman.symm_tree._arrays[RegretManager.STRAT_PATH].fill(1/actionsets)

            #now that we are done with the epoch, make some updates
            console.writeline()
            epoch += 1

            #acknowledge that we've reveived the end of steps from each slave
            signaling.SetSignal(SIGNAL_EPOCH_STOP)

            #now, wait for all OUTCOMM buffers to be reset to 0
            signaling.WaitForSignal(SIGNAL_SLAVE_READY)
            signaling.SetSignal(SIGNAL_EPOCH_READY)
