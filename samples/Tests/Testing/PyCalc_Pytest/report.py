"""Uses calc.add - rename 'add' with F2 in calc.py and this file changes too."""
from calc import add, average


def total_line(a, b):
    return f"{a} + {b} = {add(a, b)}"


def summary(values):
    return f"average {average(values):.1f}"
