#imports
import commands as broker
import console
import glob
import os
import games
from engine.Regrets import RegretManager

#a sample command group with some sample commands
class Regrets(broker.CommandGroup):

    #print a regret tree
    def print(self, parameters, path=[]):

        #get our regret manager
        r = broker.state.setdefault("regretman",RegretManager())

        #list all regrets at this path
        #for child in r.symm_tree.children(path):

    #eval regrets
    def eval(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #eval the node and print info
        (regrets,strategy,trained) = r.eval_training(False)
        console.writeline("Training Review of Model:")
        console.writeline("Regret Nodes: {}".format(regrets))
        console.writeline("Strategy Nodes: {} | Trained: {}".format(strategy,trained))
        console.writeline("")

        #get size info for the tree and print it out here
        size = r.symm_tree.size()        
        for sx in range(len(size)):
            #calculate level sparsity
            density = r.symm_tree.leveldensity(sx)

            #summarize sparsity
            if float(size[sx]["used"]) > 0:
                total_density = float(density[-1]) / float(size[sx]["used"]) / float(size[sx]["shape"]) * 100
            else:
                total_density = 0

            #print that info
            console.writeline("LEVEL {}: {} wide, {}% filled: {}% density :: {} entries - {} avail".format(
                str(sx).rjust(2),
                str(size[sx]["shape"]).rjust(4),
                "{:4.2f}".format(size[sx]["used"] / size[sx]["total"] * 100).rjust(6),
                "{:4.2f}".format(total_density).rjust(6),
                size[sx]["used"],
                size[sx]["total"] - size[sx]["used"]
            ))

    #remove regrets
    def kill(self, parameters):
        #kill all npy files
        console.writeline("Killing {}...".format(parameters[0]))
        for file in glob.glob("{}/*.npy".format(parameters[0])): os.remove(file)

        #kill the trace file
        t = open("{}/trace.txt".format(parameters[0]),"w")
        t.close()

    #create regrets
    def create(selfself, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #open the specified file
        console.writeline("Configuring regrets {}...".format(parameters[0]))
        r.configure(format(parameters[0]),games.registeredGames)
        console.writeline("Creating regrets {}...".format(parameters[0]))
        r.create(parameters[0])
        console.writeline("Ready to play {}".format(r.settings["game"]))

    #open regrets (on disk)
    def open(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #open the specified file
        console.writeline("Configuring regrets {}...".format(parameters[0]))
        r.configure(format(parameters[0]),games.registeredGames)        
        console.writeline("Opening regrets {}...".format(parameters[0]))
        r.open(parameters[0])
        console.writeline("Ready to play {}".format(r.settings["game"]))

    #configure regrets using regretfile with whatever the defaults are (open or load)
    def init(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #open the specified file
        console.writeline("Configuring regrets {}...".format(parameters[0]))
        r.configure(format(parameters[0]),games.registeredGames)
        console.writeline("Initializing regrets {}...".format(parameters[0]))
        r.initialize()
        console.writeline("Ready to play {}".format(r.settings["game"]))

    #load regrets (into memory)
    def load(self, parameters):
        #get current or create new regret manager in broker state
        r = broker.state.setdefault("regretman",RegretManager())

        #open the specified file
        console.writeline("Configuring regrets {}...".format(parameters[0]))
        r.configure(format(parameters[0]),games.registeredGames)        
        console.writeline("Loading regrets into memory from {}...".format(parameters[0]))
        r.load(parameters[0])
        console.writeline("Ready to play {}".format(r.settings["game"]))

    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("init",self.init,1,"Initializes regrets based on config file",["PATH","The regret path to configure"])
        broker.registerCommand("open",self.open,1,"Opens regrets on disk",["PATH","The regret path to open"])
        broker.registerCommand("load",self.load,1,"Loads regrets into shared memory from disk",["PATH","The regret path to load"])
        broker.registerCommand("create", self.create, 1, "Creates regrets on disk",["PATH", "The regret path to open"])
        broker.registerCommand("eval",self.eval,0,"Evalulates currently loaded regrets")
        broker.registerCommand("kill",self.kill,1,"Kills regrets at path",["PATH","The regret path to kill"])

#register our command group
broker.registerCommandGroup("Regrets", Regrets())