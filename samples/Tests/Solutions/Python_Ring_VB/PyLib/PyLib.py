def Add(a, b):
    """Adds."""
    return a + b

def Greet(name):
    return "Hello " + name

def Log(msg):
    import sys; print("LOG", msg, file=sys.stderr)
