import os

def Add(a, b):
    return a + b

def Where():
    return [os.getcwd(), os.environ.get('RAD_PROJECT'), os.environ.get('RAD_PROJECT_PATH')]
