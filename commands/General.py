#imports
import commands as broker
import console
import sys

#general commands for the browser
class General(broker.CommandGroup):

    #get a global state variable
    def get(self, parameters):

        #the value in first parameter is the path to the state register
        #split by . and there could be multiple levels of state
        registers = parameters[0].split(".")
        registers.reverse()

        #step through registers looking for them in state
        state = broker.state
        while len(registers) > 0:
            #get the next register
            register = registers.pop()
            state = state.get(register,None)

            #quit if done
            if state == None: registers = []

        #if we got to the end of our search and didn't find the register, let the user know
        if state == None:
            #we couldn't find the reigster -> let the user know
            console.writeline("Could not locate register {}".format(parameters[0]))
        else:
            #get the state variable (if available)
            console.writeline("{} = {}".format(parameters[0]),state)
    
    #a simple test command
    def exit(self,parameters):

        #let the user know, then exit the browser
        console.writeline("Shutting down browser...")
        sys.exit(0)
        
    #the help command provides help on broker commands
    #this is an introspective command
    def help(self, parameters):

        #if no command name is provided, list all commands and return
        if len(parameters) == 0:

            #step through all commands and print their help
            console.writeline("Available Commands:")
            console.writeline("Type help [command] to see more details about a specific command")
            for c in broker.commands:
                console.writeline(c + " " * (15-len(c)) + broker.commands[c]["desc"])

            #return control
            return

        #get the command name needing help
        command = parameters[0]
        
        #if the command doesn't exist, let them know
        if not broker.commandExists(command):

            #print out a message and return control
            console.writeline("Unknown command {}.  Type help for a list of commands.".format(command))
            return

        #get the command
        command = broker.commands[command.upper()]

        #print the command description
        console.writeline(command["desc"])
        console.writeline("")

        #print all command details
        details = False
        for d in command["help"]:
            console.writeline(d)
            details = True

        #that was the specifics
        if details: console.writeline("")


    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("exit",self.exit,0,"Exits the browser")
        broker.registerCommand("help",self.help,0,"Displays help",["HELP [COMMAND]","","COMMAND - name of the command to get help on"])

#register our command group
broker.registerCommandGroup("General", General())
