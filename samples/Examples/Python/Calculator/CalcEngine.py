# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""CalcEngine - the calculator's logic, kept apart from the form (no Tk here, easy to test).

The engine works like a pocket calculator: digits build the entry, an operator stores it, "=" applies
the pending operator (pressing "=" again repeats the last operation), and the memory keys MC / MR / M+ / M-
work on a separate memory value.  Decimal arithmetic avoids 0.1 + 0.2 = 0.30000000000000004.

Other languages of the project can call it through RAD Hub, e.g. VB6: x = RadCall("CalcEngine.evaluate", "2+3*4")
"""
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext

getcontext().prec = 28
OPS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b, "*": lambda a, b: a * b, "/": lambda a, b: a / b}
SYMBOL = {"+": "+", "-": "−", "*": "×", "/": "÷"}


def fmt(value: Decimal) -> str:
    """12.50 -> '12.5', 1E+3 -> '1000'; very large/small numbers use scientific notation."""
    if value == value.to_integral_value() and abs(value) < Decimal("1e16"):
        return str(value.quantize(Decimal(1)))
    text = format(value.normalize(), "f")
    if len(text) > 18:
        text = format(value, ".10e")
    return text


class Calculator:
    def __init__(self):
        self.memory = Decimal(0)
        self.clear()

    # ------------------------------------------------------------- state
    def clear(self):
        self.entry = "0"            # what the display shows
        self.acc = None             # left operand
        self.op = None              # pending operator
        self.last = None            # (op, operand) repeated by "="
        self.fresh = True           # the next digit starts a new entry
        self.error = ""
        self.expr = ""

    def clear_entry(self):
        self.entry, self.fresh, self.error = "0", True, ""

    @property
    def value(self) -> Decimal:
        return Decimal(self.entry)

    # ------------------------------------------------------------- keys
    def digit(self, d: str):
        if self.error:
            self.clear()
        if self.fresh:
            self.entry, self.fresh = d, False
        elif len(self.entry.replace("-", "").replace(".", "")) < 16:
            self.entry = d if self.entry == "0" else self.entry + d

    def dot(self):
        if self.error:
            self.clear()
        if self.fresh:
            self.entry, self.fresh = "0.", False
        elif "." not in self.entry:
            self.entry += "."

    def backspace(self):
        if self.fresh or self.error:
            return
        self.entry = self.entry[:-1] or "0"
        if self.entry in ("-", "-0"):
            self.entry = "0"

    def sign(self):
        if self.entry != "0" and not self.error:
            self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry

    def operator(self, op: str):
        if self.error:
            return
        if self.op is not None and not self.fresh:
            self._apply()               # 2 + 3 + -> shows 5
            if self.error:
                return
        self.acc = self.value
        self.op, self.fresh, self.last = op, True, None
        self.expr = f"{fmt(self.acc)} {SYMBOL[op]}"

    def equals(self):
        if self.error:
            return
        if self.op is not None:
            operand = self.value
            self.expr = f"{fmt(self.acc)} {SYMBOL[self.op]} {fmt(operand)} ="
            self.last = (self.op, operand)
            self._apply()
            self.op = None
        elif self.last is not None:     # "=" again: repeat
            op, operand = self.last
            self.acc = self.value
            self.expr = f"{fmt(self.acc)} {SYMBOL[op]} {fmt(operand)} ="
            self.op = op
            self.entry = fmt(operand)
            self._apply()
            self.op = None
        self.fresh = True

    def _apply(self):
        try:
            result = OPS[self.op](self.acc, self.value)
        except (DivisionByZero, InvalidOperation, ZeroDivisionError):
            self.entry, self.error = "Cannot divide by zero", "div0"
            self.op, self.acc = None, None
            return
        self.entry, self.acc, self.fresh = fmt(result), result, True

    # ------------------------------------------------------------- memory
    def mem_clear(self):
        self.memory = Decimal(0)

    def mem_recall(self):
        self.entry, self.fresh = fmt(self.memory), True

    def mem_add(self, sign: int = 1):
        if not self.error:
            self.memory += sign * self.value
            self.fresh = True


def evaluate(expression: str) -> str:
    """Evaluate a simple left-to-right expression like '2+3*4' (as typed on the calculator) -> '20'."""
    c = Calculator()
    for ch in expression.replace(" ", ""):
        if ch.isdigit():
            c.digit(ch)
        elif ch == ".":
            c.dot()
        elif ch in OPS:
            c.operator(ch)
    c.equals()
    return c.entry
