
function add(a, b) { return a + b; }
function viaPhp(a, b) { return radcall("CalcP.add", a, b); }
function reenter(x) { return radcall("Calc.add", x, 1); }
function gui() { set("lblOut", "Caption", "x"); }
async function later(x) { await new Promise((r) => setTimeout(r, 20)); return radcall("CalcT.add", x, 1); }
