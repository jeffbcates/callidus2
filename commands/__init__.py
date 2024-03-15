#register all modules within this folder dynamically -> ths allows fully dynamic module additions
from os.path import dirname, basename, isfile, join
import console
import glob
import random
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')] + ["CommandGroup"]

#super globals
registeredGroups = {}
commands = {}
state = {}

#return our path (from state)
def path():
    return state.get("path","")

#this function registers a command group class
def registerCommandGroup(name,group):

    #save a reference to this command group
    registeredGroups[name] = group

    #register its commands
    group.registerCommands()

#register a command
def registerCommand(name, callable, paramCount = 0, description = "", help = []):

    #add this command by name (overwrite if needed)
    commands[name.upper()] = {"ref":callable, "params":paramCount, "desc":description, "help":help}

#is the given command name valid?
def commandExists(name):

    #does this command exist?
    return name.upper() in commands

#are the parameters for a command valid?
def requiredParams(command):

    #does the command exist?
    if not commandExists(command): return 0
        
    #are enough parameters passed?
    return commands[command.upper()]["params"]

#execute a command
def executeCommand(command, parameters):

    #call the defined function by name
    commands[command.upper()]["ref"](parameters)
        
#CommandGroup base class -> provides functionality for command state
#and allows commands (that support multi-core logic) to be tracked and executed against multiple cores
#with less effort from the individual command
class CommandGroup:

    #get help on a command
    
    #register our commands with the browser
    def registerCommands(self):
        pass
