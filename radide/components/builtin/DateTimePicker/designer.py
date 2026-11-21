"""DateTimePicker on the design surface: Value (yyyy-MM-dd [HH:mm:ss], empty = now) in the chosen Format."""
from PyQt6.QtCore import QDate, QDateTime, QTime
from PyQt6.QtWidgets import QDateTimeEdit

from radide.components.classic import apply_classic, prepare

DATE_FORMAT = {"Short": "yyyy-MM-dd", "Long": "dddd, dd MMMM yyyy", "Time": "HH:mm:ss"}


def create(parent, props, ctx):
    w = QDateTimeEdit(parent)
    w.setCalendarPopup(True)
    return prepare(w)


def _value(w, p, ctx):
    fmt = p.get("Format", "Short")
    w.setDisplayFormat(DATE_FORMAT.get(fmt, DATE_FORMAT["Short"]))
    value = str(p.get("Value") or "").strip()
    dt = QDateTime.currentDateTime()
    if value:
        d = QDate.fromString(value[:10], "yyyy-MM-dd")
        t = QTime.fromString(value[-8:], "HH:mm:ss")
        if d.isValid():
            dt.setDate(d)
        if t.isValid():
            dt.setTime(t)
    w.setDateTime(dt)


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_value)
