#to train our model on how it should abstract data
#we need to track the individual game states for a certain amount of time
#then analyze those game states to decide how best to abstract them (no idea how we'll do this yet)

import copy
import console
import numpy as np
    
class GameStateAbstractor:

    #internally store all game states in an array
    #this may get large if we are dealing with very big games
    #with very complicated game states
    stateValues = {}
    stateCounts = {}

    #analyze the game state proivded (adding its info to the summary we are tracking)
    def analyzeState(self, gameState):

        #for every game state logged to the buffer, add its unique values to the state value dictionary item of the same name
        #so that our state values dictionary contains an array of unique values for each state value exposed to us
        keys = list(gameState.keys())
        for key in keys:

            #get the value
            value = gameState[key]

            #as long as this is not a tuple, list, or dictionary
            if not type(value) in (list, tuple, dict):

                #if the value is not already in our values array add it
                if value not in self.stateValues.setdefault(key,[]):
                    
                    #there is a new value
                    self.stateValues[key].append(value)

                    #add to the counts for that value
                    counts = self.stateCounts.setdefault(key,[])
                    counts.append(1)

                else:

                    #get the index of the value and add an occurance for that value
                    index = self.stateValues[key].index(value)
                    self.stateCounts[key][index] += 1

    #now that we have abstracted all our state values and occurances, what should we do with them?
    def abstractStates(self):

        #do something awesome
        x = 1