"""A tiny calculator library - the code under test."""


def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b


def grade(score):
    if score >= 90:
        return "A"
    elif score >= 50:
        return "Pass"
    return "Fail"


def average(values):
    if not values:
        return 0
    return sum(values) / len(values)


def never_tested(x):
    # no test calls this: Run with Coverage shows these lines in red
    y = x * 2
    return y + 1
