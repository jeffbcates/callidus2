#
# COMMODITY
#
# COMMODITY is a one player game where you can buy and sell an arbitrary commodity
# with a value that fluctuates in a wave-like pattern (similar to stock prices) throughout the game
# you have a limited amount of resources, and a limited number of rounds per game.

# The goal of the game is to make the most profit through your trades as possible
#
# Obviously, the name of the commodity is "Widget"

#imports
import csv
import games
import console
import random
import numpy as np
from engine.GameAbstractor import GameAbstractor
from engine.Player import Player
from engine.HumanPlayer import HumanPlayer
from engine.Callidus import Callidus

#the game abstractor for Roshambo
class CommodityAbstractor(GameAbstractor):

    #we need to track a price history for commodity
    #this is how many game steps we should track
    priceHistory = 50
    rounds = 20
    steps = 30

    #we need to restore game state from round state
    def restore_game_state(self, round_state, player_state):

        #for FLIP - game state and round state are the same
        return round_state

    #return the list of valid actions for this game (given game state)
    #for kuhn - they are always the same
    def valid_actions(self, game_state):
        #start with full action set
        actions = self.game_actions()

        ###TWEAK VALIDITY OF ACTIONS BASED ON ROUND###

        #how much cash do we have
        cash = game_state["cash"]

        #we can only buy up to the amount of cash we have on-hand
        for name in actions:
            #get the action dictionary
            action = actions[name]

            #calculate the total price of this action (for all symbols)
            price = sum([game_state["symbols"][symbol]["price"] for symbol in action["symbols"]])
            maxbuy = int ( cash / price )

            #calculate the total shares for this symbol set (we have to assume you buy/sell in equal increments)
            maxsell = max([game_state["symbols"][symbol]["shares"] for symbol in action["symbols"]])
            symbol = action["symbols"][0]

            #if this is a "buy all" type action, adjust the static value
            if action["type"] == "B" and action.get("all",False):
                action["static"] = maxbuy
                if maxbuy <= 0: action["valid"] = 0

            #if this is a sell all action - adjust static value
            if action["type"] == "S" and action.get("all",False):
                action["static"] = 0
                if maxsell <= 0: action["valid"] = 0

            #disable actions with static amounts above the max values
            if action["type"] == "B" and action["static"] > maxbuy: action["valid"] = 0
            if action["type"] == "S" and action["static"] > maxsell: action["valid"] = 0

            #for this game, you cannot hold shares over rounds, that's what makes it a round
            #because we calculate our "seed" money (which determines utility) at the beginning of each round
            if action["type"] == "H" and game_state["step"] >= self.steps - 1 and game_state["symbols"][symbol]["shares"] > 0: 
                action["valid"] = 0

        #return our actions
        return actions

    #is an action valid?
    def valid_action(self, game_state, action):
        return action["valid"] == 1

    #generate a human readable regret path
    def friendly_regret_path(self, game_state, player, majorDelim="|", minorDelim=","):

        #start the path with the players and their hole cards
        path = "{}{}{}{}{}".format(
            #round
            game_state["round"],
            majorDelim,

            #step
            game_state["step"],
            majorDelim,

            #price
            #game_state["price"]
            0

        )

        #now add all history 
        #path += game_state["flips"]

        #return that path
        return path

    #generate a regret path given game state
    def gen_regret_path_multisymbol(self, game_state, player):

        #is this the last round?  if so, we have to sell
        lastround = 1 if game_state["round"] == self.rounds - 1 else 0

        #quartile the steps of the game
        step = 4
        if game_state["step"] < self.steps - 1:
            step = self.abstract_amount(game_state["step"], 0, self.steps - 1, 4)

        #the beginning of the path is simple - just about how far we are into the game
        path = [
            (lastround, 0),
            (step, 1)
        ]

        #we will need to know the game click to calculate symbol profits, etc
        click = game_state["click"]

        #for each symbol we have available
        #add info to the path for that symbol
        for symbol in ["SOXL"]: #game_state["symbols"]:

            #get the symbol info to work with easier
            symInfo = game_state["symbols"][symbol]

            #would selling now be profitable?
            #and if so how much would we profit (or lose)?
            profitable = 1
            profit = 0
            if symInfo["shares"] > 0:
                #is this a profitable move?
                profitable = 2 if symInfo["basis"] < symInfo["price"] else 0

                #how profitable or unprofitable would this move be?
                profit = abs(symInfo["price"] - symInfo["basis"] )
                profit = self.abstract_amount(profit, 0, 19, 20)

            #add if this symbol is profitable and its profit to path
            path += [
                (profitable, 2),
                (profit, 3)
            ]

            #calculate direction of the price wave
            price = symInfo["price"]
            for phist in [1,3,6,12,24,48]:
                path.append ( ( 1 if price > self.game.price(click-phist, symbol=symbol) else 0 , len(path) ) )

            #calculate history of volumn
            vhigh = symInfo["highestv"]
            vlow = symInfo["lowestv"]
            for vhist in [0,1,3,6,12,24,48]:
                volumn = self.abstract_amount(self.game.volumn(click-vhist, symbol=symbol), vlow, vhigh, 20)
                path.append( (volumn, len(path)) )

        #return that path
        return path

    #generate a regret path given game state
    def unpack_regret_path_supersimplified(self, path):

        #our output path
        output = []

        #step through the path given and build an output path
        for p in path:

            if p[1] == 0: output += ["Last Round? {:.0f}".format(p[0])] #round
            if p[1] == 1: output += ["Step Qaurtile? {:.0f}".format(p[0])] #step
            if p[1] == 2: output += ["Profitable? {:.0f}".format(p[0])] #cash
            if p[1] == 3: output += ["Profit {:0.2f}-{:.2f}".format(*self.unpack_amount(p[0],0,19,20))] #profit

            #waveform
            if p[1] >= 4 and p[1] <= 9: output += ["Wave{}? {:.0f}".format(p[1]-3,p[0])] #cash

            #waveform
            if p[1] >= 10: output += ["Vol{} ? {:.0f}".format(p[1]-10,p[0])] #cash

        #return that output
        return output

    #return a summary state for the game in a dictionary
    def gen_summary_state(self, game_state):

        #calculate potential profit for each symbol
        profit = 0
        for symbol in game_state["symbols"]:
            symInfo = game_state["symbols"][symbol]
            profit += ( symInfo["price"] - symInfo["basis"] ) * symInfo["shares"]

        #build the state
        state = {
            "cash":game_state["cash"],
            "shares":0,
            "price":0,
            "basis":0,            
            #"shares":game_state["shares"],
            #"price":game_state["price"],
            #"basis":game_state["basis"],
            "profit":profit
        }

        #return that state
        return state

class Commodity(games.Game):

    #redefine the name of our game
    name = "Commodity"
    use_amounts = True
    seats = 1
    commodities = 1
    rounds = 20
    steps = 30
    priceHistory = 50
    abstractor = None
    history = []
    symbols = {}

    #this game uses a csv file to track the price of commodities over time so its static
    def __init__(self):

        #create our abstractor
        self.abstractor = CommodityAbstractor(self)

        #open the file and step through all rows
        with open("games/Commodity/wave.csv") as waveFile:

            #open the wave file
            reader = csv.reader(waveFile,delimiter=",")
            header = True

            #step through all rows in the wave file and load each into our wave list
            #except the first (Header) row
            for line in reader:
                #do not load the header into our wave, load that somewhere else
                if header:

                    #the header contains the definition of our commodities
                    c = 0
                    for i in range(1,len(line),2):
                        self.symbols[line[i]] = c
                        c += 1

                    #no longer a header row
                    header = False

                else:
                    #the data is stored in rows with the date/time as first column (we don't need)
                    #and then pairs of price/volume for each commodity
                    self.history.append([(float(line[i]),float(line[i+1])) for i in range(1,len(line),2)])

    #the wave function will return price and volume of a commodity at a given "click" -> row in wave file
    def wave(self, click, commodity=1, symbol=None):
        #get commodity from the symbol if provided
        if symbol != None: commodity = self.symbols[symbol]
        else: commodity -= 1

        #return that wave
        return self.history[click][commodity]

    #the price function will return the price (only) at a given click
    def price(self, click, commodity=1, symbol=None):
        return self.wave(click,commodity,symbol)[0]

    #the volumn function will return the volumn only at a given click
    def volumn(self, click, commodity=1, symbol=None):
        return self.wave(click,commodity,symbol)[1]

    #has our game finished? -> we have 3 rounds, then 1 round of judging and round 5 means finished (#4 zero based)
    def finished(self, game_state):
        return game_state.get("round",0) >= self.rounds

    #has the round finished?  this is simple in flip, it's always finished
    def roundFinished(self, game_state):

        #if we are past the last round we are finished
        if game_state["round"] >= self.rounds: return True

        #if we are past the max number of allowed steps we are finished
        if game_state["step"] >= self.steps: return True

        #if we have no history, we are not finished
        if len(game_state["history"]) == 0: return False

        #if we are step 0 we are not finished (this prevents the game from skipping from round 1 to 20
        #without player input because the history check below shows the sell action that ended the prior round
        if game_state["step"] == 0: return False

        #if our last action was to sell and we have no more shares of any symbol
        #then we are done
        if game_state["history"][-1][0][0] == "S": 
            if sum([game_state["symbols"][symbol]["shares"] for symbol in self.symbols]) == 0:
                return True

        #we are not finished
        return False

    #describe our game
    def description(self):
        return "The exciting game of buying and selling commodities."

    # display given game state
    def display(self, game_state, prefix=""):
        # gather some basic info from game state
        #cash = game_state["cash"]
        #shares = game_state["shares"]
        utility = self.utility(game_state)
        round = game_state["round"]

        # print that info out
        print(prefix + "Round {}, Cash: {}, Shares: {}, Utility: {}".format(round, cash, shares, utility))

    #increment basis -> adds shares purchased to our basis history
    def increment_basis(self, basis_history, price, amount):

        #just add an item
        basis_history.append((price,amount))

    #decrement basis -> removes shares purchased from our basis history until we've satisfied the amount passed
    def decrement_basis(self, basis_history, price, amount):

        #how many shares have we sold
        shares = 0
        while shares < amount:

            #get total shares available from first history item
            hprice,hshares = basis_history[0]

            #if there are more shares in history than we still need
            if hshares > amount - shares:
                #reduce history share amount by the # of shares we still needed
                basis_history[0] = (hprice, hshares - (amount-shares))

                #increase shares retrieved by the amount we need (ending loop)
                shares = amount

            else:

                #add shares from history and pop history item
                shares += hshares
                basis_history.pop(0)

        #we are done!
        
    #calculate basis -> determines average share basis price based on all buys we've made
    def calculate_basis(self, basis_history):

        #start with no shares and no value
        shares = 0
        value = 0

        #step through all history
        for h in basis_history:
            shares += h[1]
            value += h[0] * h[1]

        #now we have total value and total shares, return average
        if shares == 0: return 0
        else: return value / shares


    #what is the utility of a player
    def utility(self, game_state, player):

        #value cash more than shares
        return game_state["cash"] - game_state["seed"]

    #how much is at risk in the game - for Flip, it's always 2
    def risk(self, game_state, player):
        return 1

    #is an action valid?
    def validAction(self, game_state, action):
        return self.abstractor.valid_action(game_state,action)

    #step back to player -> if currently the players turn
    #will step that turn, then all turns until the players turn again
    def stepBackToPlayer(self, game_state, player):
        #since this is a 1-player game we just need 1 step and its our players turn again
        return self.step(game_state)

    #step the game until the players turn or game is finished
    def stepToPlayer(self, game_state, player):

        #if the round is finished, we need to step to the next round
        if self.roundFinished(game_state): 
            return self.step(game_state)

        #since this is a one player game we never have to do anything
        return game_state

    #trade a symbol in the game state ("B" means buy and "S" means sell)
    def trade(self, game_state, symbol, amount, actionType):

        #get the symbol info
        symInfo = game_state["symbols"][symbol]

        #get the price of the symbol at the current game click
        price = self.price(game_state["click"], symbol=symbol)

        #if the player is buying, reduce cash and increase shares
        if actionType == "B":

            #reduce cash by share price X amount
            #and increase shares by amount
            game_state["cash"] -= price * amount
            symInfo["shares"] += amount

            #increment basis history by this new purchase
            self.increment_basis(symInfo["basis_history"],price,amount)

            #calculate basis from history
            symInfo["basis"] = self.calculate_basis(symInfo["basis_history"])

        #if selling, increase cash and reduce shares
        if actionType == "S":

            #reduce cash by share price X amount
            #and increase shares by amount
            game_state["cash"] += price * amount
            symInfo["shares"] -= amount

            #decrement basis history
            self.decrement_basis(symInfo["basis_history"],price,amount)

            #calculate basis from history
            symInfo["basis"] = self.calculate_basis(symInfo["basis_history"])


    # step a round -> very simple in flip
    def step(self, game_state):

        #if the game is finished, return game state and do nothing
        if self.finished(game_state):

            #return our game state
            return game_state

        #if the round is finished, move to the next round
        if self.roundFinished(game_state):

            #increase the round and reset step
            game_state["round"] += 1
            game_state["step"] = 0

            #our cash is now our seed
            game_state["seed"] = game_state["cash"]

            #return game state
            return game_state

        #the faces of the coin are pregenerated so that our training
        #will effectively 
        round = game_state["round"]
        
        #valid actions are static in flip
        #possible action attributes are : min, max, valid, and static
        #when static is set - the player does not get a choice of value
        actions = self.abstractor.valid_actions(game_state)

        #get the players action
        history = self.players[0].declare_action(actions, {"hint":"NONE"}, game_state)+(self.players[0].name,self.players[0].guid)
        actionName = history[0]
        amount = history[1]

        #add to game history
        game_state["history"].append(history)
        game_state["actions"] += actionName

        #for each symbol in the action
        action = actions[actionName]
        for symbol in action["symbols"]:

            #get the amount to sell of this symbol (sometimes it might be all shares)
            amount = game_state["symbols"][symbol]["shares"] if action["all"] and action["type"] == "S" else action["static"]

            #trade that symbol -> symbol, amount, and action type
            self.trade(game_state, symbol, amount, action["type"])

        #move to the next step and next click (click doesn't reset per round and starts at a random history of the overall wave)
        game_state["step"] += 1
        game_state["click"] += 1

        #get the next price in our price history
        #and store it in the current price value
        #notice that we skip ahead 5 entries so that we always have at least 5 of history
        price = self.price(game_state["click"], symbol=symbol)
        volumn = self.volumn(game_state["click"], symbol=symbol)

        #for each symbol, update the low and high values for that symbol
        for symbol in self.symbols:
            symInfo = game_state["symbols"][symbol]
            price = self.price(game_state["click"], symbol=symbol)
            volumn = self.volumn(game_state["click"], symbol=symbol)

            #update symbol price and volumn
            symInfo["price"] = price
            symInfo["volumn"] = volumn

            #update low and high as needed
            if price < symInfo["low"]: symInfo["low"] = price 
            if price > symInfo["high"]: symInfo["high"] = price

            #update low and high as needed on volumn
            if volumn < symInfo["lowv"]: symInfo["lowv"] = volumn
            if volumn > symInfo["highv"]: symInfo["highv"] = volumn

        #finally, return the new state
        return game_state

    #setup a game -> given players returns an initial game state
    def setup(self, players):

        #make a copy of the players
        self.players = [players[0]]

        #now reset the game and return that new state
        return self.reset({})

    # reset the game state
    def reset(self, game_state):
        # get random cards for each of our players
        game_state = {}
        game_state["history"] = []
        game_state["actions"] = ""
        game_state["round"] = 0
        game_state["basis_history"] = []
        game_state["basis"] = 0

        #update abstractor steps and price history to match ours
        self.abstractor.steps = self.steps
        self.abstractor.priceHistory = self.priceHistory

        #arbitray high / low prices
        lowest = 10
        highest = 1000

        #setup standard values for the game
        game_state["rounds"] = self.rounds
        game_state["steps"] = self.steps
        game_state["seed"] = 10000
        game_state["cash"] = game_state["seed"]
        game_state["payoff"] = 0
        game_state["step"] = 0

        #start at a random spot in history somewhere between: (1) priceHistory and (2) the last step we can run a full game
        startClick = random.randint(self.priceHistory, len(self.history) - (self.steps * self.rounds))
        game_state["click"] = startClick

        #initialize symbols - each symbol contains its own dictionary with information about that symbol - price, history, etc
        game_state["symbols"] = {}
        for symbol in self.symbols:
            #get the internal symbol index
            idx = self.symbols[symbol]

            #build the dictionary for this symbol
            game_state["symbols"][symbol] = {
                "price" : self.price(startClick , symbol=symbol),
                "volumn" : self.volumn(startClick , symbol=symbol),
                "shares" : 0,
                "basis" : 0,
                "basis_history" : [],
                "lowest" : np.min([float(h[idx][0]) for h in self.history]),
                "highest" : np.max([float(h[idx][0]) for h in self.history]),
                "lowestv" : np.min([float(h[idx][1]) for h in self.history]),
                "highestv" : np.max([float(h[idx][1]) for h in self.history]),
                "low" : np.min([float(h[idx][0]) for h in self.history[0:startClick+1]]),
                "high" : np.max([float(h[idx][0]) for h in self.history[0:startClick+1]]),
                "lowv" : np.min([float(h[idx][1]) for h in self.history[0:startClick+1]]),
                "highv" : np.max([float(h[idx][1]) for h in self.history[0:startClick+1]])
            }

        #based on starting click, set lowest highest high/low info
        game_state["lowest"] = np.min([float(h[0][0]) for h in self.history])
        game_state["highest"] = np.max([float(h[0][0]) for h in self.history])
        game_state["lowestv"] = np.min([float(h[0][1]) for h in self.history])
        game_state["highestv"] = np.max([float(h[0][1]) for h in self.history])

        # return that game state
        return game_state


    # play a single game of kuhn poker
    def play(self, game_state:dict=None, players=[]):

        #if players are not provided, create a human player for testing
        if len(players) == 0: players = [games.HumanPlayer("Jeff", self)]

        #get a new game state if initial state not provided
        if game_state == None: game_state = self.setup(players)

        #run through our rounds until finished
        while not self.finished(game_state):
            game_state = self.step(game_state)

        # call game end message for boht players
        winner = "NONE"
        for p in players:
            p.receive_round_result_message(winner, {}, game_state)

        # return final game state if anyone out there cares
        return game_state

#register our game
games.registerGame(Commodity())
