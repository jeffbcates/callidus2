#imports
import commands as broker
import console
import time
from engine.Regrets import RegretManager, InformationSet

#a sample command group with some sample commands
class BrowserCommands(broker.CommandGroup):

    #generates a path from a string
    def flattenPath(self, path):

        #return a flattened string path from array of tuples
        return "\\".join(map(str,["{}:{}".format(p[0],p[1]) for p in path]))

    #generates a path from a string
    def genPath(self, pathString):

        #return blank string as empty array
        if pathString == "": return []

        #split the path into its tuples
        return [tuple(map(int,p.split(":"))) for p in pathString.split("\\")]

    #list current path contents
    def ls(self,parameters):

        #assume depth
        depth = 0

        #get our regretman reference
        r = broker.state.setdefault("regretman",RegretManager())
        
        #get our current path from settings (Stored as string)
        path = self.genPath(broker.state.setdefault("path",""))
        
        #unpack the location
        _,shape = r.symm_tree.get(path,include_type=True)

        #infosets are only children
        if shape == r.INFOSET_PATH:
            infoSet = InformationSet(path,r.symm_tree,False)
            console.writeline("\n" + " " * depth * 2 + "Information Set Contents:")
            console.writeline(" " * depth * 2 + "{} Reads {} Writes".format(infoSet.reads(),infoSet.writes()))
            console.writeline(" " * depth * 2 + "Average Strategy: " + str(infoSet.get_average_strategy()))
            console.writeline(" " * depth * 2 + "Strat Sum: " + str(infoSet.strategy()))
            console.writeline(" " * depth * 2 + "Regrets: " + str(infoSet.regrets()))
            console.writeline()

        #this is not an infoset, show the children
        else:

            #list all the children of this node
            for child in r.symm_tree.children(path):
                #get display name of the node
                displayName = "{}:{} - {}".format(child[0],child[1],r.game_abstractor.unpack_regret_path([(child[0],child[1])])[0])

                #print the node name and regrets
                console.writeline(" " * depth * 2 + displayName + " Regrets ")

    #change dictionary method
    def cd(self, parameters):

        #we only use the first parameter
        param = parameters[0]

        #get the current path
        path = self.genPath(broker.state.setdefault("path",""))

        #two special keywords
        if param == ".." and len(path) > 0: path.pop(-1)
        elif param == "\\": path.clear()
        else: path += self.genPath(param)

        #save path back to state
        broker.state["path"] = self.flattenPath(path)


    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("ls",self.ls,0,"List regrets at path",[])
        broker.registerCommand("cd",self.cd,1,"Change path",[])

#register our command group
broker.registerCommandGroup("BrowserCommands", BrowserCommands())


