from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Point:
    def __init__(self, x, y, label):
        self.x, self.y, self.label = x, y, label


def square(n):
    result = n * n
    return result


class Form1(Form1Designer):
    """Debugger test: expandable Locals/Watch, hit counts, logpoints, threads, attach."""

    def Form1_Load(self):
        numbers = [3, 1, 4, 1, 5]
        p = Point(10, 20, "corner")
        info = {"name": "RAD", "tags": ["ide", "vb"]}
        total = 0
        for i in range(len(numbers)):
            total += square(numbers[i])
        print("total=", total, info["name"], p.label)


if __name__ == "__main__":
    Form1().show()
