# (c) 2026 Musoftware - https://musoftwares.com - MIT License
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-guestbook")
    SITE_NAME = "Flask Guestbook"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
