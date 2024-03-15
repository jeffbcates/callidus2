from engine.Player import Player
import console

#HumanPlayer - implementation for an interactive human player for any kind of game
class HumanPlayer ( Player):

    #init player
    def __init__(self, name, game):
        super().__init__(name,game)

    #declare an action, returning an action name and amount
    def declare_action(self, valid_actions, round_state, game_state=None):

        #keep this simple
        console.writeline("=============================")
        console.writeline("Game State: {}".format(game_state))
        console.writeline("Round State: {}".format(round_state))
        console.writeline("-----------------------------")
        console.writeline("{} - It's Your Turn:".format(self.name))

        #get the player action
        console.writeline("Valid Actions: {}".format(valid_actions))
        console.write("Action?: ")
        action = console.prompt().upper()

        #if the game uses amounts, get the amount
        #otherwise, return ZERO
        if self.game.use_amounts:

            #if this action has a static amount, use it and be done
            amount = valid_actions[action].get("static",None)

            #if the amount is not valid, we probably need to get one
            if amount == None:
                console.write("Amount?: ")
                amount = float(console.prompt())

        else:

            #the game doesn't use amounts, just return zero
            amount = 0

        #end of display
        console.writeline("=============================")

        #return action, amount
        return action, amount

    def receive_game_start_message(self, game_state):
        console.writeline("-----------------------------")
        console.writeline("{} - The Game is Afoot!:".format(self.name))
        console.writeline("-----------------------------")


    def receive_round_start_message(self, round_count):
        console.writeline("-----------------------------")
        console.writeline("{} - Round {} Begins:".format(self.name,round_count))
        console.writeline("-----------------------------")

    def receive_game_update_message(self, action, round_state):
        console.writeline("-----------------------------")
        console.writeline("{} - Something Happened:".format(self.name))
        console.writeline("Round State: {}".format(round_state))
        console.writeline("-----------------------------")


    def receive_round_result_message(self, winners, player_state, round_state):
        console.writeline("-----------------------------")
        console.writeline("{} - The Game is Over:".format(self.name))
        console.writeline("Winners: {}".format(winners))
        console.writeline("Player State: {}".format(player_state))
        console.writeline("Round State: {}".format(round_state))
        console.writeline("-----------------------------")


