#for debuggin
import cProfile
import pstats

import console
import random
import copy
import numpy as np
import time
import multiprocessing
import games
from games import Game
from engine.Signaling import Signaling
from engine.Callidus import Callidus
from engine.Regrets import RegretManager
from engine.Regrets import StrategyManager
from engine.Regrets import InformationSet
from engine.Traceable import Traceable
from engine.Trainee import Trainee

class Analyzer (Traceable):

    #our internals
    regretMan = None
    trainee = None

    #run a game with a player and return value
    def simulate(self, simulation, game:Game, regretman:RegretManager, settings:dict, players):

        #an epoch is 1,000 iterations of the game
        nashGames = settings.get("nashGames",1000)
        argmax = settings.get("argmax",True)

        #configure the players
        [c.configure(regretman, argmax) for c in players]

        #assume the tracing player is the first player
        tracePlayer = players[0]
        self.trainee = tracePlayer

        #get game start time (we will write this out to the trace file)
        starttime = int(time.time())
        self.epoch = starttime

        #get a starting game state given our players
        gameState = game.setup(players)

        #to keep nash simple,we only generate nash value for the trace player
        games, wins, loses, utility, risked = 0,0,0,0,0

        #with cProfile.Profile() as profile:
        #run through all nash games
        for step in range(1,nashGames+1):

            #set step as step
            self.step = step

            #display progress to the console
            console.progress("Simulating " + simulation,step,nashGames)

            #reseting the game will shift player positions as well
            gameState = self.game.reset(gameState)
            roundWins, roundLoses = 0,0

            #step through the game until it completes
            while not game.finished(gameState):

                #get the step and round before we step the game
                #that is what we are going to trace
                round, gameStep = gameState.get("round",0), gameState.get("step",0)

                #step the game
                gameState = game.step(gameState)

                #if the game is finished, get utility
                util = game.utility(gameState,tracePlayer) if game.roundFinished(gameState) else 0

                #try to get a strategy from the trace player (might not be available)
                #otherwise, use the default strategy
                if tracePlayer.lastInfoSet != None:
                    strategy = tracePlayer.lastInfoSet.get_average_strategy()
                else:
                    strategy = regretman.get_default_strategy()

                #trace the game state
                self.trace(
                    starttime,
                    simulation,
                    step,
                    round,
                    gameStep,
                    tracePlayer.lastAction,
                    util,
                    *strategy,
                    *game.abstractor.gen_summary_state(gameState).values()
                )

                #if the round is finished, step the game
                if game.roundFinished(gameState):

                    #add to utility (we do this at the end of the round
                    utility += game.utility(gameState,tracePlayer)
                    risked += game.risk(gameState,tracePlayer)

                    #track round winning
                    if game.isWinner(gameState,tracePlayer): roundWins +=1
                    else: roundLoses += 1

                    #step the game
                    gameState = game.step(gameState)

            #the game is finished, so add to game count and win/loss count
            games += 1
            wins += 1 if roundWins >= roundLoses else 0
            loses += 1 if roundWins < roundLoses else 0

            #ps stats for the run
            #ps = pstats.Stats(profile)
            #ps.sort_stats('cumtime','tottime')
            #ps.print_stats(20)
            #console.writeline("")
            #console.prompt("done!")

        #return games, wins, utility
        return (games,wins,utility, wins/games, utility/games)

    #the following will calculate the approximate nash value for the various initial states of the game
    def nash(self, game:Game, regretman:RegretManager, settings:{}):

        #if a seed is defined, use it
        seed = settings.get("randomSeed",0)
        if seed == 0: seed = random.randint(1,1000)
            
        #an array of utility for every initial state
        #the game itself will articulate initial state and value
        #and we'll store them here and calculate/display nash
        nashValue = {}

        #seed the random number generator if a seed was provided - JBC added 2/8/24
        game.setup([Callidus("Cal",game),Callidus("Cal2",game)])

        #save a reference to the regret manager and game for iterating
        self.regretMan = regretman
        self.game = game
        
        #start our trace and write out header
        self.openTrace(regretman.filename, "nash.txt")
        genericFields = ["trace","simulation","game","round","step","action","utility"]
        self.traceHeader(*genericFields,*game.abstractor.game_actions().keys(), *game.abstractor.gen_summary_state(game.reset({})).keys())

        #simulate with control -> set seed so both games are the game
        random.seed(seed)
        control = self.simulate("Control",game,regretman,settings,[Trainee("p{}".format(p),game) for p in range(0,game.seats)])

        #simulate with callidus -> reset seed so we get the exact same game
        random.seed(seed)   
        actual = self.simulate("Callidus",game,regretman,settings,[Callidus("p{}".format(p),game) for p in range(0,game.seats)])

        #now at the end of all those games, display the nash stats
        console.writeline("")
        console.writeline("Game Nash Value:")
        console.writeline("")
        console.writeline("Control: {:.2f}% Win Ratio, Avg Utility = {:.2f}".format(control[3] * 100,control[4]))
        console.writeline("Callidus: {:.2f}% Win Ratio, Avg Utility = {:.2f}".format(actual[3] * 100,actual[4]))
        console.writeline("Edge: {:.2f}% Win Ratio, {:.2f} Utility".format( ( actual[3] - control[3]) * 100, actual[4] - control[4]))
        console.writeline("")



