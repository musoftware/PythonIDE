import sys

from .core import count_words


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    text = " ".join(argv) or "the quick brown fox jumps over the lazy dog the end"
    for word, n in count_words(text).most_common(3):
        print(f"{word}: {n}")
    return 0
