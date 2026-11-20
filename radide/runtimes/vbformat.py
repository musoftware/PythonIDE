"""VB6 Format$() for the BASIC interpreter.

Supports the named formats (General Number, Currency, Fixed, Standard, Percent, Scientific, Yes/No,
True/False, On/Off, General/Long/Medium/Short Date, Long/Medium/Short Time) and user-defined formats:

* numbers: sections ``pos;neg;zero;null``, ``0 # . ,`` (thousands and scaling), ``%``, ``E+ E- e+ e-``,
  literals ``- + $ ( ) space``, ``\\x`` and ``"text"``;
* dates/times: ``c d dd ddd dddd ddddd dddddd w ww m mm mmm mmmm q y yy yyyy h hh n nn s ss ttttt``
  ``AM/PM am/pm A/P a/p AMPM`` (``m``/``mm`` after ``h`` or before ``s`` = minutes);
* strings: ``@ & < > !``.

Dates use the day/month order the interpreter already prints (dd/mm/yyyy) and the invariant
"." decimal / "," thousands separators.
"""
from __future__ import annotations

import datetime as _dt
from decimal import ROUND_HALF_UP, Decimal

SHORT_DATE = "dd/mm/yyyy"
LONG_DATE = "dddd, d mmmm yyyy"
MEDIUM_DATE = "dd-mmm-yy"
LONG_TIME = "hh:nn:ss"
MEDIUM_TIME = "hh:nn AM/PM"
SHORT_TIME = "hh:nn"

_NAMED_NUM = {
    "currency": "#,##0.00;(#,##0.00)",
    "fixed": "0.00",
    "standard": "#,##0.00",
    "percent": "0.00%",
    "scientific": "0.00E+00",
}
_NAMED_DATE = {
    "long date": LONG_DATE, "medium date": MEDIUM_DATE, "short date": SHORT_DATE,
    "long time": LONG_TIME, "medium time": MEDIUM_TIME, "short time": SHORT_TIME,
}
_DATE_LETTERS = set("dmyhnswqtc")
_EPOCH = _dt.datetime(1899, 12, 30)


# ----------------------------------------------------------------- helpers
def _split_sections(fmt: str) -> list[str]:
    out, cur, i, q = [], "", 0, False
    while i < len(fmt):
        c = fmt[i]
        if c == '"':
            q = not q
        elif c == "\\" and not q and i + 1 < len(fmt):
            cur += fmt[i:i + 2]
            i += 2
            continue
        elif c == ";" and not q:
            out.append(cur)
            cur = ""
            i += 1
            continue
        cur += c
        i += 1
    out.append(cur)
    return out


def _tokens(sec: str):
    """Yield ("lit", text) or ("ch", char) items."""
    i = 0
    while i < len(sec):
        c = sec[i]
        if c == '"':
            j = sec.find('"', i + 1)
            j = len(sec) if j < 0 else j
            yield ("lit", sec[i + 1:j])
            i = j + 1
        elif c == "\\" and i + 1 < len(sec):
            yield ("lit", sec[i + 1])
            i += 2
        elif c == "*" and i + 1 < len(sec):         # fill character: ignored
            i += 2
        elif c == "_" and i + 1 < len(sec):         # Excel-style padding: ignored
            i += 2
        else:
            yield ("ch", c)
            i += 1


def _unquoted(sec: str) -> str:
    return "".join(t for k, t in _tokens(sec) if k == "ch")


def _is_date_format(sec: str) -> bool:
    plain = _unquoted(sec).lower()
    if any(c in plain for c in "0#@&"):
        return False
    return any(c in _DATE_LETTERS for c in plain.replace("am/pm", "").replace("a/p", ""))


def _round(x: float, nd: int) -> Decimal:
    q = Decimal(1).scaleb(-nd)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------- numbers
def _format_number(n: float, sec: str, signed: bool) -> str:
    toks = list(_tokens(sec))
    # locate placeholders
    exp_at = None
    for idx, (k, t) in enumerate(toks):
        if k == "ch" and t in "eE" and idx + 1 < len(toks) and toks[idx + 1] == ("ch", "+") or \
                k == "ch" and t in "eE" and idx + 1 < len(toks) and toks[idx + 1] == ("ch", "-"):
            exp_at = idx
            break
    mant = toks if exp_at is None else toks[:exp_at]
    dot = next((i for i, (k, t) in enumerate(mant) if k == "ch" and t == "."), None)
    int_part = mant if dot is None else mant[:dot]
    dec_part = [] if dot is None else mant[dot + 1:]
    int_ph = [t for k, t in int_part if k == "ch" and t in "0#"]
    dec_ph = [t for k, t in dec_part if k == "ch" and t in "0#"]
    if not int_ph and not dec_ph:          # no digits at all: literal text
        return "".join(t for _, t in toks)
    pct = sum(1 for k, t in mant if k == "ch" and t == "%")
    # thousands separator / scaling commas
    first_ph = next((i for i, (k, t) in enumerate(int_part) if k == "ch" and t in "0#"), None)
    last_ph = max((i for i, (k, t) in enumerate(int_part) if k == "ch" and t in "0#"), default=None)
    thousands = False
    scale = 0
    for i, (k, t) in enumerate(int_part):
        if k == "ch" and t == ",":
            if first_ph is not None and first_ph < i and last_ph is not None and i < last_ph:
                thousands = True
            elif last_ph is not None and i > last_ph:
                scale += 1
    x = n * (100 ** pct) / (1000 ** scale)
    nd = len(dec_ph)
    exp_txt = ""
    if exp_at is not None:
        etoks = toks[exp_at:]
        e_char, e_sign = etoks[0][1], etoks[1][1]
        e_digits = [t for k, t in etoks[2:] if k == "ch" and t in "0#"]
        rest_lits = "".join(t for k, t in etoks[2:] if not (k == "ch" and t in "0#"))
        lead = max(1, len(int_ph))
        e = 0
        if x != 0:
            import math
            e = math.floor(math.log10(abs(x))) - (lead - 1)
        m = abs(x) / (10 ** e) if x != 0 else 0.0
        if float(_round(m, nd)) >= 10 ** lead:
            e += 1
            m = abs(x) / (10 ** e)
        x = m if x >= 0 else -m
        width = e_digits.count("0")
        es = str(abs(e)).zfill(width) if width else str(abs(e))
        sign = "-" if e < 0 else ("+" if e_sign == "+" else "")
        exp_txt = e_char + sign + es + rest_lits
    d = _round(abs(x), nd)
    s = f"{d:f}"
    ip, _, dp = s.partition(".")
    if ip == "0" and "0" not in int_ph:
        ip = ""
    min_int = int_ph.count("0")
    if len(ip) < min_int:
        ip = ip.zfill(min_int)
    # decimals: drop trailing zeros that only have '#' placeholders
    keep = max((i + 1 for i, t in enumerate(dec_ph) if t == "0"), default=0)
    dp = dp[:nd]
    while len(dp) > keep and dp.endswith("0"):
        dp = dp[:-1]
    # integer digits into the placeholders (extra digits go to the leftmost one)
    out = []
    L = len(ip)
    n_int = len(int_ph)

    def digit_txt(r):          # r = position from the right (0 = units)
        ch = ip[L - 1 - r]
        return ch + ("," if thousands and r > 0 and r % 3 == 0 else "")

    k_ph = 0
    for k, t in int_part:
        if k == "ch" and t in "0#":
            r = n_int - 1 - k_ph
            if k_ph == 0 and L > n_int:
                out.extend(digit_txt(rr) for rr in range(L - 1, n_int - 1, -1))
            if r < L:
                out.append(digit_txt(r))
            k_ph += 1
        elif k == "ch" and t == ",":
            continue
        else:
            out.append(t)
    if n_int == 0 and L:
        out.insert(0, "".join(digit_txt(r) for r in range(L - 1, -1, -1)))
    if dot is not None:
        out.append(".")
        j = 0
        for k, t in dec_part:
            if k == "ch" and t in "0#":
                if j < len(dp):
                    out.append(dp[j])
                j += 1
            elif k == "ch" and t == ",":
                continue
            else:
                out.append(t)
    text = "".join(out) + exp_txt
    if signed and x < 0 and (d != 0 or exp_at is not None):
        text = "-" + text
    return text


def format_number(value: float, fmt: str) -> str:
    secs = _split_sections(fmt)
    if value is None:
        return secs[3] if len(secs) > 3 else ""
    if value == 0 and len(secs) > 2 and secs[2]:
        return _format_number(0, secs[2], False)
    if value < 0 and len(secs) > 1 and secs[1]:
        return _format_number(-value, secs[1], False)
    return _format_number(value, secs[0], True)


# ----------------------------------------------------------------- dates
def _week_of_year(d: _dt.datetime) -> int:
    jan1 = _dt.datetime(d.year, 1, 1)
    offset = (jan1.weekday() + 1) % 7          # Sunday = 0
    return (d.timetuple().tm_yday + offset - 1) // 7 + 1


def _date_tokens(fmt: str):
    """("lit", text) / ("ampm", pattern) / ("ch", letter run)."""
    out, i = [], 0
    while i < len(fmt):
        c = fmt[i]
        if c == '"':
            j = fmt.find('"', i + 1)
            j = len(fmt) if j < 0 else j
            out.append(("lit", fmt[i + 1:j]))
            i = j + 1
            continue
        if c == "\\" and i + 1 < len(fmt):
            out.append(("lit", fmt[i + 1]))
            i += 2
            continue
        for pat in ("AM/PM", "am/pm", "A/P", "a/p"):
            if fmt.startswith(pat, i):
                out.append(("ampm", pat))
                i += len(pat)
                break
        else:
            if fmt[i:i + 4].upper() == "AMPM":
                out.append(("ampm", "AMPM"))
                i += 4
                continue
            if c.isalpha():
                j = i
                while j < len(fmt) and fmt[j].lower() == c.lower():
                    j += 1
                out.append(("ch", fmt[i:j]))
                i = j
            else:
                out.append(("lit", c))
                i += 1
    return out


def format_date(d: _dt.datetime, fmt: str) -> str:
    out = []
    merged = _date_tokens(fmt)
    has_ampm = any(k == "ampm" for k, _ in merged)
    letters = [(idx, t.lower()) for idx, (k, t) in enumerate(merged) if k == "ch" and t[:1].isalpha()]
    for idx, (k, t) in enumerate(merged):
        if k == "lit":
            out.append(t)
            continue
        if k == "ampm":
            am = d.hour < 12
            out.append({"AM/PM": "AM" if am else "PM", "am/pm": "am" if am else "pm",
                        "A/P": "A" if am else "P", "a/p": "a" if am else "p",
                        "AMPM": "AM" if am else "PM"}[t])
            continue
        low = t.lower()
        hour = d.hour % 12 or 12 if has_ampm else d.hour
        if low[0] == "m":
            # minutes when right after an hour token or right before a seconds token
            pos = [p for p, (i2, _) in enumerate(letters) if i2 == idx][0]
            prev = letters[pos - 1][1] if pos > 0 else ""
            nxt = letters[pos + 1][1] if pos + 1 < len(letters) else ""
            if len(low) <= 2 and (prev.startswith("h") or nxt.startswith("s")):
                out.append(str(d.minute).zfill(len(low)))
                continue
            out.append({1: str(d.month), 2: f"{d.month:02d}", 3: d.strftime("%b"),
                        4: d.strftime("%B")}.get(len(low), d.strftime("%B")))
        elif low[0] == "d":
            n = len(low)
            if n == 5:
                out.append(format_date(d, SHORT_DATE))
            elif n >= 6:
                out.append(format_date(d, LONG_DATE))
            else:
                out.append({1: str(d.day), 2: f"{d.day:02d}", 3: d.strftime("%a"), 4: d.strftime("%A")}[n])
        elif low[0] == "y":
            n = len(low)
            out.append(str(d.timetuple().tm_yday) if n == 1 else f"{d.year % 100:02d}" if n == 2
                       else str(d.year))
        elif low[0] == "h":
            out.append(str(hour) if len(low) == 1 else f"{hour:02d}")
        elif low[0] == "n":
            out.append(str(d.minute) if len(low) == 1 else f"{d.minute:02d}")
        elif low[0] == "s":
            out.append(str(d.second) if len(low) == 1 else f"{d.second:02d}")
        elif low[0] == "w":
            out.append(str((d.weekday() + 1) % 7 + 1) if len(low) == 1 else str(_week_of_year(d)))
        elif low[0] == "q":
            out.append(str((d.month - 1) // 3 + 1))
        elif low[0] == "t" and len(low) == 5:
            out.append(format_date(d, LONG_TIME))
        elif low == "c":
            out.append(general_date(d))
        else:
            out.append(t)
    return "".join(out)


def general_date(d: _dt.datetime) -> str:
    if d.hour == d.minute == d.second == 0:
        return format_date(d, SHORT_DATE)
    if d.date() == _EPOCH.date():
        return format_date(d, LONG_TIME)
    return format_date(d, SHORT_DATE + " " + LONG_TIME)


# ----------------------------------------------------------------- strings
def format_string(s: str, fmt: str) -> str:
    secs = _split_sections(fmt)
    sec = secs[0] if s != "" or len(secs) < 2 else secs[1]
    toks = list(_tokens(sec))
    upper = any(k == "ch" and t == ">" for k, t in toks)
    lower = any(k == "ch" and t == "<" for k, t in toks)
    left_to_right = any(k == "ch" and t == "!" for k, t in toks)
    phs = [i for i, (k, t) in enumerate(toks) if k == "ch" and t in "@&"]
    if upper:
        s = s.upper()
    elif lower:
        s = s.lower()
    if not phs:
        return s + "".join(t for k, t in toks if not (k == "ch" and t in "<>!"))
    chars = list(s)
    fill = {}
    if left_to_right:
        for i in phs:
            fill[i] = chars.pop(0) if chars else None
        extra_after = "".join(chars)
        extra_before = ""
    else:
        for i in reversed(phs):
            fill[i] = chars.pop() if chars else None
        extra_before = "".join(chars)
        extra_after = ""
    out = [extra_before]
    for i, (k, t) in enumerate(toks):
        if i in fill:
            c = fill[i]
            out.append(c if c is not None else (" " if t == "@" else ""))
        elif k == "ch" and t in "<>!":
            continue
        else:
            out.append(t)
    out.append(extra_after)
    return "".join(out)


# ----------------------------------------------------------------- entry point
def vb_format(value, fmt, to_str, to_num, to_date, empty=None):
    """Format(value, fmt) - conversion helpers are passed in by the interpreter."""
    fmt = "" if fmt is None or fmt is empty else to_str(fmt)
    low = fmt.strip().lower()
    if value is None or value is empty:
        secs = _split_sections(fmt)
        if value is None and len(secs) > 3:
            return secs[3]
        if value is empty and not fmt:
            return ""
    if isinstance(value, _dt.datetime):
        if not fmt or low == "general date":
            return general_date(value)
        if low in _NAMED_DATE:
            return format_date(value, _NAMED_DATE[low])
        if _is_date_format(_split_sections(fmt)[0]):
            return format_date(value, fmt)
        value = to_num(value)
    if not fmt:
        return to_str(value)
    if low in ("yes/no", "true/false", "on/off"):
        a, b = low.split("/")
        try:
            on = to_num(value) != 0
        except Exception:  # noqa: BLE001
            on = bool(value)
        return (a if on else b).capitalize() if a != "on" else ("On" if on else "Off")
    if low == "general number":
        return to_str(to_num(value))
    if low in _NAMED_NUM:
        try:
            n = to_num(value)
        except Exception:  # noqa: BLE001
            return to_str(value)
        return format_number(n, _NAMED_NUM[low])
    if low in _NAMED_DATE or low == "general date":
        d = to_date(value)
        return general_date(d) if low == "general date" else format_date(d, _NAMED_DATE[low])
    first = _split_sections(fmt)[0]
    plain = _unquoted(first)
    if isinstance(value, str) and any(c in plain for c in "@&<>!") and not any(c in plain for c in "0#"):
        return format_string(value, fmt)
    if _is_date_format(first):
        try:
            return format_date(to_date(value), fmt)
        except Exception:  # noqa: BLE001
            return to_str(value)
    if any(c in plain for c in "@&") and not any(c in plain for c in "0#"):
        return format_string(to_str(value), fmt)
    try:
        n = to_num(value)
    except Exception:  # noqa: BLE001 - non-numeric text with a number format is returned unchanged
        return to_str(value)
    return format_number(float(n) if not isinstance(n, int) else n, _NAMED_NUM.get(low, fmt))
