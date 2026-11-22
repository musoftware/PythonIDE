// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module CalcEngine - the arithmetic of the calculator, kept apart from the form so it can be reused
// (other languages of a solution call it with radcall("CalcEngine.calculate", 6, "*", 7)).

/** a <op> b; division by zero gives NaN ("Error" on the display). */
function calculate(a, op, b) {
    switch (op) {
        case '+': return a + b;
        case '-': return a - b;
        case '*': return a * b;
        case '/': return b === 0 ? NaN : a / b;
        default: return b;
    }
}

/** A number for the display: at most 12 significant digits, no float noise (0.1 + 0.2 -> 0.3). */
function formatNumber(x) {
    if (!Number.isFinite(x)) return 'Error';
    return String(Number(x.toPrecision(12)));
}
