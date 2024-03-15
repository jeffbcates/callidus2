#we have a fast deep copy implementation
import engine.FastCopy as fastcopy

#a game abstractor is used by the regret manager
#so that we can process regrets by any different type of game
#each game should implement a game abstractor that takes the game
#state for a given timestep of a game and returns a unified regret path
#game state is always a dictionary describing the current game state
class GameAbstractor:

	#internal values
	#where we store settings for quick reference
	_base_actions = None
	_base_action_sets = None
	_base_shape_def = None
	_base_shape = None
	_base_levelnames = None
	_base_pathgenerator = None
	_base_pathunpacker = None

	#sometimes its helpful to know the game you are abstracting (to be able to talk to it)
	game = None

	#initialize game abstractor
	def __init__(self, game = None):
		
		#save a reference to the game we are abstracting
		self.game = game

	#once a symmtree shape is generated, this can return it quickly
	def symmtree_shape(self):
		return self._base_shape

	#we need to translate a symmtree definition into an actual symm tree and return it
	#if a definition was provided, otherwise the abstractor should override this and create a custom shape
	def gen_symmtree_shape(self):

		#our internal translation table for size multipliers
		multipliers = {
			"b":	1000000000,
			"hm":	 100000000,
			"tm":     10000000,
			"m":       1000000,
			"ht":       100000,
			"tt":        10000,
			"t":          1000,
			"h":           100,
			"o":             1
		}

		#start with an empty symmtree shape
		shape = []
		self._base_levelnames = {}

		#step through our internal shape definition (which is a 2d array of the definition of each level)
		c = 0
		for level in self._base_shape_def:

			#get the components that matter to us
			name = level[0]
			choices = level[1]
			type = level[2]
			size = level[3]
			multiplier = level[4]

			#adjust size by multiplier
			#for anything not defined - assume 1
			size *= multipliers.get(multiplier,1)

			#add this definition to our actual shape
			shape += [[choices, type, size]]

			#save a lookup for this shape by name to its level #
			self._base_levelnames[name] = c
			c += 1

		#return our shape built from the definition
		return shape

	#return the level number for a level name
	#this can be overriden, but defaults to using the shape definintion in settings.json
	def level(self, name):

		#return level number from base shape lookup table
		return self._base_levelnames[name]

	#configure an abstractor given game settings
	def configure(self, settings):

		#save off internal values
		self._base_actions = settings.get("actions",{})
		self._base_shape_def = settings.get("symmtree",[])

		#lookup and resolve the generator function by name
		generator = settings.get("pathgenerator",None)
		if generator != None: self._base_pathgenerator = getattr(self,generator)

		#lookup and resolve the generator function by name
		pathunpacker = settings.get("pathunpacker",None)
		if pathunpacker != None: self._base_pathunpacker = getattr(self,pathunpacker)

		#flatten then count our generic game actions -> those become the base actino sets
		self._base_action_sets = len(self.flatten_actions(self.game_actions()))

		#save our generic symmtree shape for reference
		self._base_shape = self.gen_symmtree_shape()

	
	#display game state
	def display(self, game_state, prefix = ""):
		pass

	#return a human readable regret path
	def friendly_regret_path(self, game_state, player, majorDelim="|", minorDelim=","):
		pass

	#generate a summary state for the game - a dictionary of only the key state fields we care about
	def gen_summary_state(self, game_state):
		#by default just return the game state (JBC 2/9/24)
		return game_state

	#generate a regret path given game state
	def gen_regret_path(self, game_state, player):

		#if we got here, that means this method was not overriden
		#and instead the game generator is defining the path generator
		#within the settings file
		return self._base_pathgenerator(game_state,player)

	#what are our path names
	def path_names(self):
		return self._base_levelnames

	#unpack a path and return a friendly name
	def unpack_regret_path(self, path):

		#if we got here, that means this method was not overriden
		#and instead the game generator is defining the path generator
		#within the settings file
		return self._base_pathunpacker(path)

	#extract and abstract info from the given game state dictionary
	def abstract_game_state(self, game_state, player):
		pass

	#extract an action name and value from a valid action for the game
	def abstract_action(self, action):
		pass

	#return the # of action sets for the game (this should be constant for each game, based on game state abstractor)
	def action_sets(self):
		#return base action sets unless overridden
		return self._base_action_sets

	#return the list of all game actions (may not be valid for every situation
	def game_actions(self):
		#return internal game actions
		return fastcopy.deepcopy(self._base_actions)

	#return valid actions for current state
	#assume all game actions are valid (game needs to override if they are not)
	def valid_actions(self, game_state):
		#by default return all game actions
		return self.game_actions()

	#is an action valid
	def valid_action(self, game_state, action):
		pass

	# return specific locations for this abstractor
	# these are for: infoset_path, regret_path, strat_path, stat_path
	# they are needed for any game but their locations can vary
	def infoset_paths(self):
		pass

	#flatten actions (some games do not have a simple array of actions)
	#we flatten more complicated action shapes into a simple arrray of choices
	def flatten_actions(self, actions:dict):
		#the default method to flatten actions is just turn them into a list
		#if you need something more complicated, you can override this function
		return list(actions.values())

	#when we are passing state to individual players, we don't pass the full
	#game state because that includes private info of other players - instead
	#the game abstractor can restore game state from the round state and player state
	#this will return an abstracted game state where the player has all their private info
	#but none of the other players private info
	def restore_game_state(self, round_state, player_state):
		pass

	#instead of the player needing to know an action amount the abstractor will know
	#how to get it -> we want as few direct dictionary references within the player as possible
	#that way the games can have different setups 
	def action_amount(self, action):

		#by default, return "static" action amount
		#this can be overridden with a custom abstractor
		return action["static"]

	#instead of the player needing to know an action name the abstractor will know
	#how to get it -> we want as few direct dictionary references within the player as possible
	#that way the games can have different setups 
	def action_name(self, action):
		
		#by default return "name" attribute from action
		#this can be overridden with a custom abstractor
		return action["name"]


	###ABSTRACTION METHODS###

	#abstract an amount given a discret # of possible values and a known range
	def abstract_amount(self, amount, low, high, buckets):

		#calculate bucket size based on # of buckets and range from low to high
		size = (high - low + 1) / buckets

		#fix for over/under min and max values
		amount = low if amount < low else high if amount > high else amount

		#calculate bucket and return it
		return int((amount - low) / size)

	#unpack an abstracted amount (returns a tuple of the range given a bucket)
	def unpack_amount(self, bucket, low, high, buckets):

		#calculate bucket size based on # of buckets and range from low to high
		#subtract 1 from buckets because bucket ZERO counts as a bucket
		size = (high - low) / (buckets - 1) 

		lowside = low + bucket * size
		highside = low + (bucket+1) * size - 1

		#return that range
		return (lowside,highside)