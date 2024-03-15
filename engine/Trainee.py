import random
from engine.Player import Player
from engine.GameAbstractor import GameAbstractor
from engine.Regrets import RegretManager

#Trainee is a dumb player where you can set the action
class Trainee(Player):

    #our locals
    nextAction:dict = None
    lastAction = None
    lastInfoSet = None
    abstractor:GameAbstractor = None

    #we are configured via the same signature as Callidus
    def configure(self, regretman:RegretManager, argmax = True):

        #we don't actually need the argmax value, just matching signature of Callidus configure

        #we just need the abstractor
        self.abstractor = regretman.game_abstractor

    #set the next action for trainee
    def setNextAction(self, nextAction:dict):
        self.nextAction = nextAction.copy()

    #declare our action (predefined in our case)
    def declare_action(self, actions, round_state, game_state):

        #if an action is set, use it
        if self.nextAction != None: action = self.nextAction

        #otherwise, choose a random action from the list of valid actions
        else: action = random.choice([action for action in self.abstractor.flatten_actions(actions) if self.abstractor.valid_action(round_state,action)])

        #get the action amount
        #use the current action amount versus the set "next action" amount
        name = self.abstractor.action_name(action)
        amount = self.abstractor.action_amount(action)

        #save as last action
        self.lastAction = name
        
        #return action name and amount
        return name, amount