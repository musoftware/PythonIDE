# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""FastApiTasks - a to-do REST API with FastAPI + SQLite and an HTML page that uses it with fetch().

Shows: path/query parameters, Pydantic models with validation (Field, Literal), status codes, HTTPException,
a Jinja2 template, static files, automatic API docs at /docs (View > FastAPI > Open /docs).

    GET    /api/tasks?done=false     list (optional filter)
    POST   /api/tasks                {"title": "...", "priority": "low|normal|high"}
    PATCH  /api/tasks/{id}           {"done": true} or {"title": "..."}
    DELETE /api/tasks/{id}
    GET    /api/stats                counts
"""
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .db import connect, row_to_dict
from pathlib import Path

BASE = Path(__file__).resolve().parent
app = FastAPI(title="FastApiTasks", description="A to-do list API made with RAD IDE", version="1.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

Priority = Literal["low", "normal", "high"]


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    priority: Priority = "normal"


class TaskPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    priority: Optional[Priority] = None
    done: Optional[bool] = None


class Task(BaseModel):
    id: int
    title: str
    priority: Priority
    done: bool
    created: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"title": "Tasks"})


@app.get("/api/tasks", response_model=list[Task])
def list_tasks(done: Optional[bool] = None):
    sql, args = "SELECT * FROM task", []
    if done is not None:
        sql, args = sql + " WHERE done = ?", [int(done)]
    order = " ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id DESC"
    with connect() as con:
        return [row_to_dict(r) for r in con.execute(sql + order, args)]


@app.post("/api/tasks", response_model=Task, status_code=201)
def add_task(task: TaskIn):
    with connect() as con:
        cur = con.execute("INSERT INTO task (title, priority) VALUES (?, ?)", (task.title.strip(), task.priority))
        return row_to_dict(con.execute("SELECT * FROM task WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, patch: TaskPatch):
    changes = patch.model_dump(exclude_none=True)
    with connect() as con:
        if con.execute("SELECT id FROM task WHERE id = ?", (task_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Task not found")
        for key, value in changes.items():
            con.execute(f"UPDATE task SET {key} = ? WHERE id = ?", (int(value) if key == "done" else value, task_id))
        return row_to_dict(con.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone())


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with connect() as con:
        if con.execute("DELETE FROM task WHERE id = ?", (task_id,)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/stats")
def stats():
    with connect() as con:
        total, done = con.execute("SELECT COUNT(*), COALESCE(SUM(done), 0) FROM task").fetchone()
    return {"total": total, "done": done, "open": total - done}
