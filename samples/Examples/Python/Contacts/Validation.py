# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Validation - checks a contact before it is saved (pure Python, no UI; used by frmContacts)."""
import re

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^\+?[0-9 ()\-]{5,20}$")


def check_contact(name: str, phone: str, email: str) -> list[str]:
    """A list of problems (empty = the contact can be saved)."""
    problems = []
    if not name.strip():
        problems.append("Name is required.")
    elif len(name.strip()) > 80:
        problems.append("Name is too long (80 characters at most).")
    if phone.strip() and not PHONE.match(phone.strip()):
        problems.append("Phone may contain digits, spaces, + ( ) - only.")
    if email.strip() and not EMAIL.match(email.strip()):
        problems.append("E-mail address is not valid.")
    return problems


def csv_line(values) -> str:
    """One CSV line (quotes doubled, fields with , " or new lines quoted)."""
    out = []
    for v in values:
        s = "" if v is None else str(v)
        if any(ch in s for ch in ',"\n\r'):
            s = '"' + s.replace('"', '""') + '"'
        out.append(s)
    return ",".join(out)
