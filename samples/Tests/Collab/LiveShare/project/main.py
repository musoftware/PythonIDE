"""Shared during the Live Share test - both IDEs edit this file at the same time."""
from lib.greet import greet


def main():
    # مرحبا - Arabic text must survive concurrent edits
    print(greet("World"))


if __name__ == "__main__":
    main()
