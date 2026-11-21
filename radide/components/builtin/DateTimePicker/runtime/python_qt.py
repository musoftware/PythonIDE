"""DateTimePicker - python-qt (PySide6) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    p, n, fmt, out, DATE_FORMATS = g.p, g.n, g.fmt, g.out, g.DATE_FORMATS
    _date_value = g.date_value
    out.append(f"self.{n}.setDisplayFormat({DATE_FORMATS.get(fmt, DATE_FORMATS['Short'])!r})")
    v = _date_value(p.get("Value", ""), fmt)
    if fmt == "Time":
        out.append(f"self.{n}.setTime(QTime.fromString({v!r}, 'HH:mm:ss'))" if v
                   else f"self.{n}.setTime(QTime.currentTime())")
    else:
        out.append(f"self.{n}.setCalendarPopup(True)")
        out.append(f"self.{n}.setDate(QDate.fromString({v!r}, 'yyyy-MM-dd'))" if v
                   else f"self.{n}.setDate(QDate.currentDate())")
