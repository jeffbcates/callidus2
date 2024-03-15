#imports
import games
import console
from engine.GameAbstractor import GameAbstractor


#the game abstractor for Roshambo
class RoshamboAbstractor(GameAbstractor):

    #we don't need to flatten actions
    def flatten_actions(self, actions):
        return actions

    #action sets -> return the # of possible actions at any time
    def action_sets(self):
        return 3 #roshambo has 3 actions at all times, and no amounts

    #we must define a symmtree shape for our game
    #this is unique to every game
    def symmtree_shape(self):

        #our symmetric tree shape
        m = 1000
        symmtree_shape = [

            #these paths are dependent on the type of game
            
            #regardless of the game -> these are always required
            (3,0, 250*m), #infoset arrays - cumulative regrets, strategy sum, and statistics                         -> 150 million paths
            (self.action_sets(),1, 250*m), #array of regrets
            (self.action_sets(),1, 250*m), #array of strategy                                                                           -> 30 million paths
            (2,0, 250*m) #read and write counts are INT                                                               -> 150 million paths
        ]

        #save the shape for later use (we won't allocate memory until a load or attach
        #method is called
        return symmtree_shape

#a sample command group with some sample commands
class Roshambo(games.Game):

    #redefine the name of our game
    name = "Roshambo"
    use_amounts = False
    seats = 2

    #our game abstractor
    abstractor = RoshamboAbstractor()

    #describe our game
    def description(self):
        return "The exciting game of rock-paper-scissors, only with a keyboard."

    #play the game
    def play(self, state):

        #start the game
        console.writeline("Let's Play Roshambo...")

        #this is going to be very simple, create 2 players
        h1 = games.HumanPlayer("Jeff", self)
        h2 = games.HumanPlayer("Bob", self)

        #there are three rounds
        h1wins = 0
        h2wins = 0
        for round in range(1,3):

            #start this round
            console.writeline("Starting round {}".format(round))

            #get players actions
            h1action,h1amount = h1.declare_action({"rock":1,"paper":2,"scissors":3},None)
            h2action,h2amount = h2.declare_action({"rock":1,"paper":2,"scissors":3},None)

            #who wins?
            if h1action == "rock":
                if h2action == "scissors": h1wins += 1
                elif h2action == "paper": h2wins += 1
            elif h1action == "paper": 
                if h2action == "rock": h1wins += 1
                elif h2action == "scissors": h2wins += 1
            elif h2action == "rock": h2wins += 1
            elif h2action == "paper": h1wins += 1

        #we are done
        if h1wins == h2wins:
            console.writeline("tie!")
        else:
            if h1wins > h2wins:
                winner_name = h1.name
            else:
                winner_name = h2.name
            console.writeline("Well, that was fun.  {} won!".format(winner_name))


#register our game
games.registerGame(Roshambo())

