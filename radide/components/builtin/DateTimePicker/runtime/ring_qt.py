"""DateTimePicker - ring-qt (RingQt) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    q, p, n, fmt, out = g.q, g.p, g.n, g.fmt, g.out
    DATE_FORMATS, _date_value = g.DATE_FORMATS, g.date_value
    out.append(f"{n}.setDisplayFormat({q(DATE_FORMATS.get(fmt, DATE_FORMATS['Short']))})")
    v = _date_value(p.get("Value", ""), fmt)
    if fmt == "Time":
        out.append(f"{n}.setTime(new qTime().fromString({q(v)}, \"HH:mm:ss\"))" if v
                   else f"{n}.setTime(new qTime().currentTime())")
    else:
        out.append(f"{n}.setCalendarPopup(true)")
        out.append(f"{n}.setDate(new qDate().fromString({q(v)}, \"yyyy-MM-dd\"))" if v
                   else f"{n}.setDate(new qDate().currentDate())")
