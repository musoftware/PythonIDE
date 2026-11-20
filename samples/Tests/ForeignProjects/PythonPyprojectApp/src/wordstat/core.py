from collections import Counter


def count_words(text: str) -> Counter:
    words = [w.strip(".,;:!?").lower() for w in text.split()]
    counts = Counter(w for w in words if w)
    return counts
