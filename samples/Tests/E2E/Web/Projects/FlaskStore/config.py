import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SITE_NAME = "FlaskStore"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
