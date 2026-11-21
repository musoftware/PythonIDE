"""python -m radide.agc MAIN.agc [--seconds S] [--keys V35E] - assemble and run headless (see machine.run_cli)."""
import sys

from .machine import run_cli

if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]))
