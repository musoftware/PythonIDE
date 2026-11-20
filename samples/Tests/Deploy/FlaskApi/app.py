"""A tiny Flask API used to test RAD IDE's Docker generator (Docker > Generate Dockerfile)."""
import os
import platform

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return "<h1>Hello from Flask in Docker</h1><p>Try <a href='/api/health'>/api/health</a></p>"


@app.get("/api/health")
def health():
    return jsonify(status="ok", python=platform.python_version(), container=os.path.exists("/.dockerenv"))


if __name__ == "__main__":
    app.run(debug=True, port=8000)
