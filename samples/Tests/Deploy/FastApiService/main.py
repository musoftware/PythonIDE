"""A tiny FastAPI service used to test RAD IDE's Docker generator."""
from fastapi import FastAPI

app = FastAPI(title="RAD IDE FastAPI test")


@app.get("/")
def root():
    return {"message": "Hello from FastAPI in Docker"}


@app.get("/items/{item_id}")
def item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
