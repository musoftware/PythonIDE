import os

BASE = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SITE_NAME = "Flask Todo"
    DATABASE = os.path.join(BASE, "instance", "todo.sqlite")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = ":memory:"
