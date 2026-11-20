"""A long-running Python program to try Debug > Attach to Process on."""
import time


def tick(count):
    doubled = count * 2
    data = {"count": count, "doubled": doubled}
    print("tick", count, data, flush=True)
    return doubled


if __name__ == "__main__":
    n = 0
    while True:
        n += 1
        tick(n)
        time.sleep(0.5)
