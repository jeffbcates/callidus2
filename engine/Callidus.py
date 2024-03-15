from engine.Player import Player
from engine.Regrets import InformationSet
import numpy as np
import random

class Callidus(Player):

    #our locals
    regret_man = None
    abstractor = None
    use_argmax = True

    #for tracing purpose (inside nash), we save the last infoset/strategy
    lastInfoSet:InformationSet = None
    lastAction = None
    lastAmount = None

    #how many of the available actions will we consider when applying a weighted strategy
    weighted_strats = 2

    #init player
    def __init__(self, name, game):

        #call super
        super().__init__(name,game)

        #settings for how we declare action
        self.use_argmax = True

    #we must connect to the regret manager to work
    def configure(self, regretman, argmax = True):

        #get regretman and abstractor references
        self.use_argmax = argmax
        self.regret_man = regretman
        self.abstractor = regretman.game_abstractor

    #declare an action, returning an action name and amount
    def declare_action(self, actions, round_state, game_state):

        #TODO: need to get all players declare actions consistent (callidus is dif than human)

        #to keep users from cheating we don't provide full game state
        #instead they have to generate a placeholder game state from round state
        #and each game abstractor is responsible for doing that however makes sense for them
        game_state = self.abstractor.restore_game_state(game_state, round_state)

        #flatten actions into a simple array using abstractor
        valid_actions = self.abstractor.flatten_actions(actions)

        #get infoset based on game state
        info_set = self.regret_man.get_information_set(game_state, self, False)

        #get average strategy from that infoset
        strat = info_set.get_average_strategy()

        #clear out invalid strategies and re-normalize
        for c in range(0,len(strat)):
            if not self.game.validAction(game_state, valid_actions[c]): strat[c] = 0

        #renormalize the actually valid strategies
        strat /= sum(strat)

        #pick best action
        #get the action from strategy
        if self.use_argmax:
            #use argmax to pick an action from our strategy
            best_action_index = np.argmax(strat)
        else:

            #get the top N strategies and their corresponding actions
            topindexes = np.argpartition(strat,self.weighted_strats * -1)[self.weighted_strats * -1:]
            topstrats = np.take(strat,topindexes)
            
            #pick a random action from those top strategies
            #but weight based on the strategy
            best_action_index = random.choices(range(len(topstrats)), weights=topstrats, k=1)[0]

            #that index is actually the index within topstrats, so use topindexes to get the original index
            best_action_index = topindexes[best_action_index]

        #get the best action from action names -> use abstractor to figure out the correct name for our action
        best_action = self.abstractor.action_name(valid_actions[best_action_index])
        
        #get the amount from actions
        action_amount = self.abstractor.action_amount(valid_actions[best_action_index])

        #update "last" references for tracing
        self.lastInfoSet = info_set
        self.lastAction = best_action
        self.lastAmount = action_amount

        #return action, amount
        return best_action, action_amount

    def receive_game_start_message(self, game_state):
        pass

    def receive_round_start_message(self, round_count):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, player_state, round_state):
        pass


