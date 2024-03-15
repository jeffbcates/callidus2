#imports
import numpy as np
from sys import stdout

#write to the console
def write(message):
    _console.write(message)

#write a line to the console
def writeline(message = ""):
    _console.writeline(message)

#write an error to the console
def error(message = ""):
    _console.writeline("ERROR: " + message)

#wait for the console (i.e. on command line wait for return key)
def wait():
    _console.wait()

#receive input from the console
def prompt(path = ""):
    return _console.prompt(path)

#display / pass progress to the console
def progress(prefix, current, total, suffix=""):
    _console.progress(prefix,current,total,suffix)

#initialize the console
def init(console):
    _console = console

#abstract base class for a console
class ConsoleAbtract():

    #write to the console
    def write(self,message):
        pass

    #write to the console with CRLF
    def writeline(self,message = ""):
        pass

    #receive input from console
    def prompt(self, path = ""):
        pass

    #display progress
    def progress(self):
        pass

#simple CLI implementation of console
class CommandConsole():
    
    #write to the console (no carriage return)
    def write(self,message):
        print(message,end="")

    #write to the console with CRLF
    def writeline(self,message = ""):
        print(message)

    #wait for the user to hit any key
    #but don't return that key
    def wait(self):
        input()

    #receive input from the console
    def prompt(self, path):
        
        #until we get non-empty input
        user_input = ""
        while user_input == "":

            #command console -> print command prompt
            print("{}>".format(path),end="")

            #get the user input
            user_input = input()

        #return that non-empty input to the caller as an array
        return user_input

    #display progress on the console
    def progress(self,prefix, current, total, suffix = ""):
        barLength = 50
        percent = float(current) * 100 / total
        arrow   = '-' * int(percent/100 * barLength - 1) + '>'
        spaces  = ' ' * (barLength - len(arrow))
        output = prefix + ': [%s%s] %d %%: %s' % (arrow, spaces, percent, suffix)
        output += ' ' * (110-len(output))
        print(output, end='\r')
        stdout.flush()

#set global numpy print options
np.set_printoptions(precision=4,suppress=True,threshold=5)

#our console
_console = CommandConsole()
