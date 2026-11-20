"""Starts the game - F5 in RAD IDE runs this file. Change the first scene or the title here."""
import os

import radgame

if __name__ == "__main__":
    radgame.run('Level1', title='HelloGame',
                folder=os.path.dirname(os.path.abspath(__file__)))
