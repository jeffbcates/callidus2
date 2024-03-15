import random

#Player - base class for any kind of player (AI or human)
class Player:

    #all players have a name and guid
    guid = ""
    name = ""
    game = None

    #all players need to call this
    def __init__(self, name, game):

        #set our name and game reference
        self.name = name
        self.game = game

        #set our guid to our name hashed plus a random number
        #we actualy concat the random number to ensure a unique hex
        self.guid = hex(hash("{}-{}".format(name,random.randrange(10000))))

    #declare an action, returning an action name and amount
    def declare_action(self, valid_actions, round_state):
        #return action, amount
        pass

    def receive_game_start_message(self, game_state):
        pass

    def receive_round_start_message(self, round_count):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, player_state, round_state):
        pass
