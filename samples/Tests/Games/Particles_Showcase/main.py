"""Starts the game - F5 in RAD IDE runs this file. Change the first scene or the title here."""
import os

import radgame

if __name__ == "__main__":
    radgame.run('Scene1', title='Particles Showcase',
                folder=os.path.dirname(os.path.abspath(__file__)))
