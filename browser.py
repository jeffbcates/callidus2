#imports
import sys
import console
import commands as broker
from commands import *
from games import *

#browser -> simple CLI for interacting with callidus
class Browser:

    #constants
    browser_version = "2.0"

    #welcome message
    def welcome(self):

        #print some basic information for the user
        console.writeline("Welcome to Callidus Browser {}".format(self.browser_version))
        console.writeline()
        console.writeline("Type any command at the prompt, or HELP for hints")
        console.writeline()

    #pipe commands - unsplits and resplits commands by comma
    #to handle piping multiple commands
    def pipe(self,commands):
        #join by space, split by comma and then return the 2-d array of commands
        return [s.strip().split() for s in " ".join(commands).split(",")]

    #main entry for the browser
    def browse(self, args = []):

        #our command broker
        console.init(console.CommandConsole())

        #print welcome
        self.welcome()

        #run commands until exit
        command = ""
        while command != "EXIT":

            try:

                #if initializing get command from args
                if len(args) > 0:
                    user_input = self.pipe(args)
                    args = []
                else: user_input = self.pipe(console.prompt(broker.path()).split())

                #step through all commands in user input
                for inputs in user_input:
                    #go no further if the command string is empty
                    if len(inputs) == 0: break

                    #get command name
                    command = inputs[0]

                    #if the command exists
                    if not broker.commandExists(command):
                        console.writeline("Unknown command " + command)
                        break

                    #are the parameters for the command valid?
                    passedParamCount = len(inputs)-1
                    requiredParamCount = broker.requiredParams(command)
                    if passedParamCount < requiredParamCount:
                        console.writeline("{} command requires {} parameters but {} were supplied.".format(command,requiredParamCount,passedParamCount))
                        console.writeline("")
                        break;

                    #the command is found and parameters are valid
                    #run the command - catch errors and display
                    broker.executeCommand(command,inputs[1:])

            except Exception as error:
                #print an error message but don't kill the whole process
                print("Error running command: " + str(error))
