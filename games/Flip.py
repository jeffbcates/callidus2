#imports
import games
import console
import random
from engine.GameAbstractor import GameAbstractor
from engine.Player import Player
from engine.HumanPlayer import HumanPlayer
from engine.Callidus import Callidus

#the game abstractor for Roshambo
class FlipAbstractor(GameAbstractor):

    #to properly abstract our game we define our paths
    STACK_INDEX = 0 #how much money we have in our stack for betting
    ROUND_INDEX = 1 #how many times the coin has flipped in the past (abstracted)
    PATH_INDEX = 2 #the obligitory path index we always need
    HISTORY_INDEX = 3 #the short of history of prior flips
    INFOSET_INDEX = 4
    REGRET_INDEX = 5
    STRATERGY_INDEX = 6
    STATS_INDEX = 7

    #return an action amount
    #given a dictionary item that is an action
    #which has been abstracted already
    def action_amount(self, action):

        #for FLIP this is simple
        #just return the static action amount
        return action["static"]

    #return the action name
    def action_name(self, action):

        #for FLIP - the name is stored in the action
        return action["name"]

    #we need to restore game state from round state
    def restore_game_state(self, round_state, player_state):

        #for FLIP - game state and round state are the same
        return round_state

    #return the list of valid actions for this game (given game state)
    #for kuhn - they are always the same
    def valid_actions(self, game_state):
        #start with full action set
        actions = self.game_actions()

        ###TWEAK VALIDITY OF ACTIONS BASED ON ROUND###

        #all actions are always valid, otherwise the game is over

        #return our actions
        return actions

    #we must define a symmtree shape for our game
    #this is unique to every game
    def symmtree_shape(self):

        #our symmetric tree shape
        m = 1000
        symmtree_shape = [

            #these paths are dependent on the type of game
            (21,0, 1), #there are 21 abstracted stack sizes (5 - 99) / 5 and 100+
            (20,0, 1*m), #there are 20 possible abstracted rounds (1..20+)
            (2,0, 600*m), #split between leaf and non-leaf paths (0=leaf, 1=history)
            (20,0, 600*m), #action history 
            
            #regardless of the game -> these are always required
            (3,0, 250*m), #infoset arrays - cumulative regrets, strategy sum, and statistics                         -> 150 million paths
            (self.action_sets(),1, 250*m), #array of regrets
            (self.action_sets(),1, 250*m), #array of strategy                                                                           -> 30 million paths
            (2,0, 250*m) #read and write counts are INT                                                               -> 150 million paths
        ]

        #save the shape for later use (we won't allocate memory until a load or attach
        #method is called
        return symmtree_shape

    #nash state of game - very simplified regret path - basically just the starting card and position of a player
    def nash_state(self, game_state, player):

        #get our round and action
        round = game_state["round"]
        action = game_state["actions"][-1]

        #return that
        return "round {} playing {}".format(round,action)

    #generate a human readable regret path
    def friendly_regret_path(self, game_state, player, majorDelim="|", minorDelim=","):

        #start the path with the players and their hole cards
        path = "{}{}{}{}".format(
            #round
            game_state["round"],
            majorDelim,

            #action
            game_state["actions"],
            majorDelim

        )

        #now add all history 
        path += game_state["flips"]

        #return that path
        return path

    #generate a regret path given game state
    def gen_regret_path(self, game_state, player):

        #abstract our stack
        stack = int(game_state["stack"]/5)
        stack = 20 if stack > 20 else stack

        #abstract our round
        round = game_state["round"]
        round = 19 if round > 19 else round

        #start our path with our stack and round
        path = [(stack,self.STACK_INDEX),(round,self.ROUND_INDEX)]

        #add in the action history (up to 20 results)
        flips = game_state["flips"]
        path += [(0 if h == "H" else 1,self.HISTORY_INDEX) for h in flips[::-1]]

        #add in our last predicted action
        #action = game_state["actions"][-1]
        #path += [(0 if h == "H" else 1, self.ACTION_INDEX) for h in action]

        #return that path
        return path

class Flip(games.Game):

    #redefine the name of our game
    name = "Flip"
    use_amounts = True
    seats = 1
    rounds = 20
    abstractor = FlipAbstractor()

    #has our game finished? -> we have 3 rounds, then 1 round of judging and round 5 means finished (#4 zero based)
    def finished(self, game_state):
        return game_state.get("stack",0) == 0 or game_state.get("round") >= 20

    #has the round finished?  this is simple in flip, it's always finished
    def roundFinished(self, game_state):
        #the round is finished if step is not zero or the game is finished
        return game_state["step"] > 0 or game_state["round"] >= 20

    #describe our game
    def description(self):
        return "The exciting game of flipping a coin and betting on it."

    # display given game state
    def display(self, game_state, prefix=""):
        # gather some basic info from game state
        stack = game_state["stack"]
        round = game_state["round"]
        actions = game_state["actions"]
        history = game_state["history"]

        # print that info out
        print(prefix + "Round {}, Stack: {}, Actions: {}, History: {}".format(round, stack, actions, history))


    #what is the utility of a player
    def utility(self, game_state, player):
        #utility is the payoff
        return game_state["payoff"]

    #how much is at risk in the game - for Flip, it's always 2
    def risk(self, game_state, player):
        return 1

    #is an action valid?
    def validAction(self, game_state, action):
        return 1

    #step back to player -> if currently the players turn
    #will step that turn, then all turns until the players turn again
    def stepBackToPlayer(self, game_state, player):
        #since this is a 1-player game we just need 1 step and its our players turn again
        return self.step(game_state)

    #step the game until the players turn or game is finished
    def stepToPlayer(self, game_state, player):
        #since this is a one player game we never have to do anything
        return game_state

    # step a round -> very simple in flip
    def step(self, game_state):

        #the faces of the coin are pregenerated so that our training
        #will effectively 
        round = game_state["round"]

        #if we want to try a different way, we can use the following
        #for a completely random roll every single iteration of every single step
        face = game_state["faces"][round]
        #face = random.choice(["H","T"])

        #valid actions are static in flip
        #possible action attributes are : min, max, valid, and static
        #when static is set - the player does not get a choice of value
        actions = self.abstractor.valid_actions(game_state)

        #on the first step, play the round
        if game_state["step"] == 0:

            #get the players action
            history = self.players[0].declare_action(actions, {"hint":face}, game_state)+(self.players[0].name,self.players[0].guid)

            #add to game history
            game_state["history"].append(history)
            game_state["actions"] += history[0]
            game_state["flips"] += face

            #if the player guessed right, add to stack and payoff
            #otherwise reduce
            if face == history[0]:

                #add to stack and payoff
                game_state["stack"] += 1
                game_state["payoff"] += 1

            else:

                #reduce stack and payoff
                game_state["stack"] -= 1
                game_state["payoff"] -= 1

            #we are now on step 2
            game_state["step"] = 1
            return game_state

        #on the second step, move the round and reset step
        if game_state["step"] > 0:

            #increase the round and reset step
            game_state["round"] += 1
            game_state["step"] = 0

        #finally, return the new state
        return game_state

    #shift player positions in the game
    def shiftPlayOrder(self, game_state):

        #reverse our list of players
        players = self.players.reverse()

        #return a new game state from those new positions
        return self.reset(players)

    #setup a game -> given players returns an initial game state
    def setup(self, players):

        #make a copy of the players
        self.players = [players[0]]

        #now reset the game and return that new state
        return self.reset({})

    # reset the game state
    def reset(self, game_state):
        # get random cards for each of our players
        game_state = {}
        game_state["history"] = []
        game_state["actions"] = ""
        game_state["flips"] = ""
        game_state["round"] = 0
        game_state["stack"] = 10
        game_state["payoff"] = 0
        game_state["step"] = 0

        #get some # of faces automatically
        game_state["faces"] = ""
        for f in range(1,30):
            game_state["faces"] += random.choice(["H","T"])

        #testing with a set pattern:
        #game_state["faces"] = "THTHTHTHTHTHTHTHTHTHT"

        # return that game state
        return game_state


    # play a single game of kuhn poker
    def play(self, game_state:dict=None, players=[]):

        #get a new game state if initial state not provided
        if game_state == None: game_state = self.setup(players)

        #run through our rounds until finished
        while not self.finished(game_state):
            game_state = self.step(game_state)

        # call game end message for boht players
        winner = "NONE"
        for p in players:
            p.receive_round_result_message(winner, {}, game_state)

        # return final game state if anyone out there cares
        return game_state

#register our game
games.registerGame(Flip())
