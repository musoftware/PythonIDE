import platform


def summary():
    lines = [f"python {platform.python_version()}", f"os {platform.system()}"]
    return lines


if __name__ == "__main__":
    for line in summary():
        print("report:", line)
