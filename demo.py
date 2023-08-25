from agent import Player
from environment import Game

# Define the game
game = Game()

# Load the players into the game
game.load_players([
    Player("Bob", killer=False, agent="gpt-3.5"),
    Player("Adam", killer=True, agent="cli"),
    Player("Jim", killer=False, agent="gpt-3.5"),
    Player("Alice", killer=False, agent="gpt-3.5"),
])

# Play the game
game.play()