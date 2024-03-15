#imports
import games
import console
import random
from engine.GameAbstractor import GameAbstractor
from engine.Player import Player
from engine.HumanPlayer import HumanPlayer
from engine.Callidus import Callidus

#the game abstractor for Roshambo
class KuhnAbstractor(GameAbstractor):

    #to properly abstract our game we define our paths
    SEAT_INDEX = 0
    HOLE_INDEX = 1
    ROUND_INDEX = 2
    PATH_INDEX = 3
    ACTION_INDEX = 4
    INFOSET_INDEX = 5
    REGRET_INDEX = 6
    STRATERGY_INDEX = 7
    STATS_INDEX = 8

    #return an action amount
    #given a dictionary item that is an action
    #which has been abstracted already
    def action_amount(self, action):

        #for KUHN this is simple
        #just return the static action amount
        return action["static"]

    #return the action name
    def action_name(self, action):

        #for KUHN - the name is stored in the action
        return action["name"]

    #we need to restore game state from round state
    def restore_game_state(self, round_state, player_state):

        #for KUHN - game state and round state are the same
        return round_state

    #return the list of valid actions for this game (given game state)
    #for kuhn - they are always the same
    def valid_actions(self, game_state):
        #start with full action set
        actions = self.game_actions()

        ###TWEAK VALIDITY OF ACTIONS BASED ON ROUND###

        #you can't fold the first round
        #if game_state["round"] == 0: actions["F"]["valid"] = 0

        #if not the first found and the last action was bet, checking will cost
        if game_state["round"] > 0:
            if game_state["history"][-1][0] == "B":
                actions["C"]["static"] = 1

        #return our actions
        return actions

    #is an action valid?
    def valid_action(self, game_state, action):
        return action["valid"] == 1

    #we must define a symmtree shape for our game
    #this is unique to every game
    def symmtree_shape(self):

        #our symmetric tree shape
        m = 1000
        symmtree_shape = [

            #these paths are dependent on the type of game
            (2,0, 1), #there are 2 possible seat positions in 2-player kuhn
            (3,0, 2*3), #there are 3 possible hole cards in 2-player kuhn (times 2 seat positions)
            (3,0, 2*3*4), #there are 4 possible rounds in 2-player kuhn (times 2 seats times 3 holes)
            (3,0, 600*m), #split between leaf and non-leaf paths (0=leaf, 1=vilan, 2=hero)
            (3,0, 300*m), #action history -> fold, check, bet
            
            #regardless of the game -> these are always required
            (3,0, 250*m), #infoset arrays - cumulative regrets, strategy sum, and statistics                         -> 150 million paths
            (self.action_sets(),1, 250*m), #array of regrets
            (self.action_sets(),1, 250*m), #array of strategy                                                                           -> 30 million paths
            (2,0, 250*m) #read and write counts are INT                                                               -> 150 million paths
        ]

        #save the shape for later use (we won't allocate memory until a load or attach
        #method is called
        return symmtree_shape

    #nash state of game - very simplified regret path - basically just the starting card and position of a player
    def nash_state(self, game_state, player):

        #get our seat and card
        seat = game_state["player_seats"][player.name]
        card = game_state["cards"][seat]

        #return that
        return "seat {} playing {}".format(seat,card)
        #return "seat {}".format(seat)

    #generate a human readable regret path
    def friendly_regret_path(self, game_state, player, majorDelim="|", minorDelim=","):

        #start the path with the players and their hole cards
        path = "{}:{}{}{}:{}{}".format(
            #first player
            game_state["player_names"][0],
            game_state["cards"][0],

            #major delim
            majorDelim,

            #second player
            game_state["player_names"][1],
            game_state["cards"][1],

            #major delim
            majorDelim
        )

        #now add all history 
        for h in game_state["history"]:
            path += "{}:{}{}".format(h[2],h[0],minorDelim)

        #remove trailing delimters
        path = path.rstrip("{}{}".format(majorDelim, minorDelim))

        #return that path
        return path

    #generate a regret path given game state
    def gen_regret_path(self, game_state, player):

        #figure out guids of players from state
        villanguid = game_state["players"][0]
        villanidx = 0
        playeridx = 1
        if villanguid == player.guid: 
            villanguid = game_state["players"][1]
            villanidx = 1
            playeridx = 0

        #get our hole from game state (J,Q,K)
        hole_card = game_state["cards"][playeridx]
        hole_val = {"J":0,"Q":1,"K":2}.get(hole_card)

        #get our street (0 -> means we go first, 1 -> means we go second, 2 -> means we checked they bet)
        #and the dealer guid
        street = game_state["round"]
        #dealer = game_state["dealer"]

        #start our path at seat position
        #add in the hole
        #add in the round
        path = [
                    (playeridx,self.SEAT_INDEX),
                    (hole_val,self.HOLE_INDEX),
                    (street,self.ROUND_INDEX),
        ]


        #to help translate actions
        path_vals = {villanguid:1,player.guid:2}
        action_vals = {"fold":0,"check":1,"bet":2}

        #step through our actions
        for history in game_state["history"]:

            #get this player and action (check, bet, fold)
            guid = history[3]
            action = history[0]

            #figure out the action name
            actionname = "bet"
            if action == "C":
                actionname = "check"
                if history[1] == 0:
                    actionname = "fold"
            elif action == "F":
                actionname = "fold"

            #add to the path
            path += [(path_vals[guid],self.PATH_INDEX)]
            path += [(action_vals[actionname],self.ACTION_INDEX)]

        #path always ends in leaf position
        path += [(0,self.ACTION_INDEX)]

        #return that path
        return path

class Kuhn(games.Game):

    #redefine the name of our game
    name = "Kuhn"
    use_amounts = True
    seats = 2
    abstractor = KuhnAbstractor()

    #has our game finished? -> we have 3 rounds, then 1 round of judging and round 5 means finished (#4 zero based)
    def finished(self, game_state):
        return game_state.get("round",0) == 4

    #in kuhn, and game and round are the same
    def roundFinished(self, game_state):
        return self.finished(game_state)

    #describe our game
    def description(self):
        return "The exciting game of 2-Player Kuhn Poker."

    # display given game state
    def display(self, game_state, prefix=""):
        # gather some basic info from game state
        pot = game_state["pot"]
        round = game_state["round"]
        cards = game_state["cards"]
        actions = game_state["actions"]

        # print that info out
        print(prefix + "Round {}, Pot: {}, Cards: {}, Actions: {}".format(round, pot, cards, actions))
        # print("===")
        # print(str(game_state))
        # print("===")


    #what is the utility of a player
    def utility(self, game_state, player):
        #get the player seat
        seat = game_state["player_seats"][player.name]

        #get the stack
        stack = game_state["stacks"][seat]

        #return difference in final and starting stack
        return stack - 2

    #how much is at risk in the game - for Kuhn, it's always 2
    def risk(self, game_state, player):
        return 2

    #is an action valid?
    def validAction(self, game_state, action):
        return action["valid"] == 1

    #step back to player -> if currently the players turn
    #will step that turn, then all turns until the players turn again
    def stepBackToPlayer(self, game_state, player):

        #quit if the game is already finished
        if self.finished(game_state): return game_state

        #get the seat of the player
        seat = game_state["player_seats"][player.name]

        #if it is already the players turn, step the game
        if game_state["current_player"] == seat: game_state = self.step(game_state)

        #now step to the player and return
        return self.stepToPlayer(game_state, player)


    #step the game until the players turn or game is finished
    def stepToPlayer(self, game_state, player):
        #get the player seat
        seat = game_state["player_seats"][player.name]

        #keep going until the game is finished or its the current players turn
        while not self.finished(game_state) and game_state["current_player"] != seat:

            #step the game
            game_state = self.step(game_state)

        #return that state
        return game_state

    # step a round
    def step(self, game_state):
        # extract cards from game state
        cards = game_state["cards"]

        #valid actions are static in kuhn
        #possible action attributes are : min, max, valid, and static
        #when static is set - the player does not get a choice of value
        actions = self.abstractor.valid_actions(game_state)

        # trigger round 1
        if game_state["round"] == 0:

            # player 1 always starts
            history = self.players[0].declare_action(actions, {"card":cards[0]}, game_state)+(self.players[0].name,self.players[0].guid)
            game_state["history"].append(history)

            # reduce stack of player 1 appropriately, and increase pot as well
            game_state["actions"] += history[0]
            game_state["stacks"][0] -= history[1]
            game_state["pot"] += history[1]

            #if for some dumb reason the first player folds
            #we still need to handle that (remember that Callidus learns purely by experience)
            if history[0] == "F":
                game_state["round"] = 3
                game_state["current_player"] = 2
            else:
                # move to next round and return game state
                game_state["round"] = 1
                game_state["current_player"] = 1
                return game_state

        # trigger round 2
        if game_state["round"] == 1:

            # player 2 always follows (there is no folding)
            history = self.players[1].declare_action(actions, {"card":cards[1]}, game_state)+(self.players[1].name,self.players[1].guid)
            game_state["history"].append(history)

            # reduce stack of player 1 appropriately
            game_state["actions"] += history[0]
            game_state["stacks"][1] -= history[1]
            game_state["pot"] += history[1]

            # move to next round and return game state
            # if player 1 checked and player 2 bet, play returns to player 1
            if history[0] == "B" and game_state["history"][-2][0] == "C":
                game_state["round"] = 2
                game_state["current_player"] = 0

                #return control
                return game_state

            else:
                # skip to last round, there is no round 3
                game_state["round"] = 3
                game_state["current_player"] = 2  # 2 indicates none of the players

                #we do not exit, just proceeding to judging round right away

        # trigger round 3
        if game_state["round"] == 2:

            # if player 1 checked and player 2 bet, play returns to player 1
            if game_state["history"][-1][0] == "B" and game_state["history"][-2][0] == "C":
                # act on player 1
                history = self.players[0].declare_action(actions, {"card": cards[0]}, game_state)+(self.players[0].name,self.players[0].guid)
                game_state["history"].append(history)

                # reduce stack of player 1 appropriately
                game_state["actions"] += history[0]
                game_state["stacks"][0] -= history[1]
                game_state["pot"] += history[1]

            # move to next round and return game state
            game_state["round"] = 3
            
            #we do not return game state right now because the game is over - proceeding to judging round

        # round 4 is the "judging" round where we pick a winner
        if game_state["round"] == 3:

            #if the last player folded, they are not the winner
            winner = -1
            if game_state["history"][-1][0] == "F":
                loser = game_state["history"][-1][2]
                if game_state["player_seats"][loser] == 0: winner = 1
                else: winner = 0

            #if noone folded and the stacks are equal, this is a showdown
            elif game_state["stacks"][0] == game_state["stacks"][1]:
                # both players matched bet, the best card wins
                if cards[0] == "K" or cards[1] == "J":
                    winner = 0
                else:
                    winner = 1
            else:
                # whoever bet the most wins
                if game_state["stacks"][0] < game_state["stacks"][1]:
                    # player 1 bet more so player 1 wins
                    winner = 0
                else:
                    # player 2 bet more so player 2 wins
                    winner = 1

            # award the pot to the winners
            game_state["stacks"][winner] += game_state["pot"]
            game_state["pot"] = 0
            game_state["payoff"] = game_state["stacks"][winner] - 2  # we started with 2 chips
            game_state["round"] = 4
            game_state["winner"] = winner
            game_state["winner_name"] = self.players[winner].name
            return game_state

        # all other rounds, just return game state
        return game_state

    #shift player positions in the game
    def shiftPlayOrder(self, game_state):

        #reverse our list of players
        players = self.players.reverse()

        #return a new game state from those new positions
        return self.reset(players)

    #setup a game -> given players returns an initial game state
    def setup(self, players):

        #make a copy of the players
        self.players = [players[0], players[1]]

        #now reset the game and return that new state
        return self.reset({})

    # reset the game state
    def reset(self, game_state):
        # get random cards for each of our players
        game_state = {}
        kuhn_cards = ['J', 'Q', 'K']
        game_state["cards"] = random.sample(kuhn_cards, 2)
        game_state["history"] = []
        game_state["round"] = 0

        #our player array is already setup (that was called in the setup method)
        #but we need to reverse play order at each call to reset
        self.players.reverse()

        # the player names don't necessarily align to index of players, so track that in game state
        game_state["player_seats"] = {}
        game_state["player_seats"][self.players[0].name] = 0
        game_state["player_seats"][self.players[1].name] = 1
        game_state["player_guids"] = {}
        game_state["player_guids"][self.players[0].guid] = 0
        game_state["player_guids"][self.players[1].guid] = 1
        game_state["player_names"] = [self.players[0].name, self.players[1].name]

        #we also need to track players
        #in several ways to make it easy to find the player by index or guid
        game_state["players"] = [self.players[0].guid, self.players[1].guid]

        # setup stacks and pot - assume both players have 2 stack and each ante 1
        game_state["stacks"] = [1, 1]
        game_state["pot"] = 2
        game_state["current_player"] = 0
        game_state["actions"] = ""

        # return that game state
        return game_state


    # play a single game of kuhn poker
    def play(self, game_state:dict=None, players=[]):

        #shuffle players
        random.shuffle(players)

        # get a new game state if initial state not provided
        if game_state == None: game_state = self.setup(players)

        # trigger all 4 rounds, don't worry if some rounds are not applicable
        game_state = self.step(game_state)
        game_state = self.step(game_state)
        game_state = self.step(game_state)
        game_state = self.step(game_state)

        # call game end message for boht players
        winner = game_state["winner"]
        for p in players:
            p.receive_round_result_message(winner, {}, game_state)

        # return final game state if anyone out there cares
        return game_state

#register our game
games.registerGame(Kuhn())
