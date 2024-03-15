#imports
import commands as broker
import console
from engine.Player import Player

#TODO: make the broker handle player types just like it does games
from engine.HumanPlayer import HumanPlayer
from engine.Callidus import Callidus

#register all modules within this folder dynamically -> ths allows fully dynamic module additions
from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')] + ["Game"]

#globals
registeredGames = {}

#this function registers a command group class
def registerGame(game):

    #save a reference to this game by its name
    registeredGames[game.name] = game

#register a new game
def registerGame(game):

    #add or replace definition
    registeredGames[game.name.upper()] = game

#does the given game exist?
def gameExists(name):

    #does this command exist?
    return name.upper() in registeredGames


#Game - base class for a game of any kind
class Game:

    #the name of a game
    name = "Empty Game"
    seats = 0
    rounds = 1

    #some games do not need amounts, so for human players we don't show them
    use_amounts = True

    #a description of the game
    def description(self, broker):
        return "This game does not describe itself :("

    #placeholder - to play a game
    #if players are not supplied, the game should setup its own players
    def play(self, state, players=[]):
        return

    #setup a game - given players creates a new game state
    #used internally and during training
    def setup(self, players):
        pass

    #reset the state of a game (for training purpose and used internally)
    def reset(self, game_state):
        pass

    #step the state of a game (for training purpose and used internally)
    def step(self, game_state):
        pass

    #step the state of the game until the given player's turn or the game is finished
    #if it happens to be the given players turn, this will call the players action
    #and all other actions until returning to the player
    def stepBackToPlayer(self, game_state, player):
        pass

    #step the state of the game until the given player's turn or the game is finished
    #if it is currently the players turn, does nothing
    def stepToPlayer(self, game_state, player):
        pass

    #has the game ended (per game state)
    def finished(self, game_state):
        pass

    #has the round ended (per game state)
    def roundFinished(self, game_state):
        pass

    #what is the round # => override if somehow differnt
    def round(self, game_state):
        return game_state["round"]

    #did a player win
    def isWinner(self, game_state, player):
        #if utility is non zero, the player won
        return self.utility(game_state, player) > 0

    #what is the utility for a player (i.e. how much they won)
    def utility(self, game_state, player):
        pass

    #how much is at risk in the game
    def risk(self, game_state, player):
        pass

    #is a particular action valid given the game state?
    def validAction(self, game_state, action):
        pass

    #shift player positions in the game
    #this is equivelant to the dealer changing in poker
    #shift player positions in the game
    def shiftPlayOrder(self, game_state):

        #reverse our list of players
        players = self.players.reverse()

        #return a new game state from those new positions
        return self.reset(players)

#the following attaches commands to the browser for our games
class Games(broker.CommandGroup):

    #play a game
    def play(self,parameters):

        #if no parameters were specified, list all available games to play
        if len(parameters) == 0:
            #list the games available
            console.writeline("Which game would you like to play?")
            console.writeline("")
            for game in registeredGames:
                console.writeline("{}  {}".format(game,registeredGames[game].description()))

            #and get out of here
            return

        #get the game name
        gameName = parameters[0].upper()

        #does the game exist
        if not gameExists(gameName):
            console.writeline("Unknown game: {}".format(gameName))
            return

        #start the game
        console.writeline("Starting Game: {}".format(gameName))
        game = registeredGames[gameName]

        ###FOR NOW SETUP PLAYERS MANUALLY###
        #setup a human player to play against callidus
        h1 = HumanPlayer("Jeff", game)

        #setup callidus to play kuhn
        #using the regretman loaded in broker state
        h2 = Callidus("Cal", game)
        h2.configure(broker.state["regretman"])

        #add the two players to an array for reference in game
        players = [h1,h2]

        #we pass broker state to the game so it acn reference state objects
        #like the regret manager
        game.play(players=players)

    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("play",self.play,0,"Play a game by name or list available games to play")

#register our command group -> this hooks us into the command browser with our custom game-specific commands
broker.registerCommandGroup("Games", Games())
