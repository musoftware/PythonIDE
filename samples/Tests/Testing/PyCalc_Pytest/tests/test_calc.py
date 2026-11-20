import pytest

from calc import add, average, divide, grade


def test_add():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-2, -3) == -5


def test_divide():
    assert divide(10, 4) == 2.5


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)


def test_grade_pass():
    # this test FAILS on purpose: grade(75) is "Pass", not "B"
    assert grade(75) == "B"


@pytest.mark.parametrize("values, expected", [([1, 2, 3], 2), ([10], 10)])
def test_average(values, expected):
    assert average(values) == expected


@pytest.mark.skip(reason="example of a skipped test")
def test_later():
    assert False
