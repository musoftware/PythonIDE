"""FastAPI Items - a CRUD API (SQLAlchemy + SQLite) and a page that uses it."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_session
from .models import Item
from .schemas import ItemCreate, ItemOut, ItemUpdate

BASE = Path(__file__).resolve().parent
DEMO = [("Keyboard", "Mechanical, Arabic / English", 49.9), ("Mouse", "Wireless", 19.5),
        ("Monitor", "27 inch", 189.0)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        if s.scalar(select(Item.id).limit(1)) is None:
            s.add_all(Item(name=n, description=d, price=p) for n, d, p in DEMO)
            s.commit()
    yield


app = FastAPI(title="FastAPI Items", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    items = session.scalars(select(Item).order_by(Item.id)).all()
    return templates.TemplateResponse(request, "index.html", {"items": items, "count": len(items)})


@app.get("/items", response_model=list[ItemOut])
def list_items(q: str | None = None, skip: int = Query(0, ge=0), limit: int = Query(50, le=200),
               session: Session = Depends(get_session)):
    stmt = select(Item).order_by(Item.id).offset(skip).limit(limit)
    if q:
        stmt = stmt.where(or_(Item.name.ilike(f"%{q}%"), Item.description.ilike(f"%{q}%")))
    return session.scalars(stmt).all()


@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(data: ItemCreate, session: Session = Depends(get_session)):
    item = Item(**data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def _get(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/items/{item_id}", response_model=ItemOut)
def read_item(item_id: int, session: Session = Depends(get_session)):
    return _get(session, item_id)


@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, session: Session = Depends(get_session)):
    item = _get(session, item_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, session: Session = Depends(get_session)):
    session.delete(_get(session, item_id))
    session.commit()
