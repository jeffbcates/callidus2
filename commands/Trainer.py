#imports
import commands as broker
import console
import games
import multiprocessing
from engine.Regrets import RegretManager
from engine.Trainer import Trainer
from engine.Test import Test
from engine.Analyzer import Analyzer

#a sample command group with some sample commands
class TrainerCommands(broker.CommandGroup):


    #testing multi
    def multi(self,parameters):

        #create a new trainer
        t = Test()

        #open the specified file
        console.writeline("Testing multi")
        
        #train the game using the settings loaded from JSON file for regrets
        t.multi()

        #we are done training
        console.writeline("Testing complete!")

    #reset regrets
    def reset(self, parameters):

        #get the regret manager
        regretman = broker.state.setdefault("regretman",RegretManager())

        #get action sets 
        actionsets = len(regretman.settings.get("actions",[1]))

        #if we want to reset after this epoch, or reset every N epochs, do so
        console.writeline("Reseting Regrets...")
        regretman.symm_tree._arrays[RegretManager.STRAT_PATH].fill(1/actionsets)


    #run nash evaluation on a game
    def nash(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #create a new trainer
        a = Analyzer()

        #open the specified file
        console.writeline("Evaluating {} Nash".format(parameters[0]))
        
        #train the game using the settings loaded from JSON file for regrets
        a.nash(game=games.registeredGames[parameters[0].upper()], regretman=r, settings=r.settings)

    #train regrets on a game
    def train(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #configure from file if needed
        if len(parameters) > 0:
            console.writeline("Configuring regrets {}...".format(parameters[0]))
            r.configure(format(parameters[0]),games.registeredGames)        
            
        #now intialize (this will only do something if not already done)
        console.writeline("Initializing regrets...")
        r.initialize()

        #create a new trainer
        t = Trainer()

        #open the specified file
        console.writeline("Training regrets {}...".format(r.filename))
        
        #train the game using the settings loaded from JSON file for regrets
        t.train(game=games.registeredGames[r.settings["game"]], regretman=r, settings=r.settings)

        #we are done training
        console.writeline("Training complete!")

    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("train",self.train,0,"Trains regrets against a game",["PATH","The regret path to open and train"])
        broker.registerCommand("nash",self.nash,1,"Calculates nash of a game",["GAME","The game to review"])
        broker.registerCommand("multi",self.multi,0,"Test multi",[])
        broker.registerCommand("reset",self.reset,0,"Resets current regret strategies (be careful)",[])

#register our command group
broker.registerCommandGroup("Trainer", TrainerCommands())
