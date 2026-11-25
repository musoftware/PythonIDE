// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in JavaScript with a RAD IDE form.
// Shows: many Button handlers sharing one helper, keyboard input (KeyPress on the display: digits,
// + - * / . % = Enter, BackSpace, Escape), a history ListBox (double-click a line to reuse its result),
// a View menu that hides/shows the history, and a separate module (CalcEngine.js) with the math.

let entry = '0';          // number being typed
let acc = null;           // left operand
let op = '';              // pending operator: + - * /
let fresh = true;         // the next digit starts a new number

function Form1_Load(e) { show_(); }

// ------------------------------------------------------------------ digits and operators
function cmd0_Click(e) { digit('0'); }
function cmd1_Click(e) { digit('1'); }
function cmd2_Click(e) { digit('2'); }
function cmd3_Click(e) { digit('3'); }
function cmd4_Click(e) { digit('4'); }
function cmd5_Click(e) { digit('5'); }
function cmd6_Click(e) { digit('6'); }
function cmd7_Click(e) { digit('7'); }
function cmd8_Click(e) { digit('8'); }
function cmd9_Click(e) { digit('9'); }
function cmdDot_Click(e) { digit('.'); }
function cmdAdd_Click(e) { operator('+'); }
function cmdSub_Click(e) { operator('-'); }
function cmdMul_Click(e) { operator('*'); }
function cmdDiv_Click(e) { operator('/'); }
function cmdEq_Click(e) { equals(); }

function cmdClear_Click(e) {
    entry = '0'; acc = null; op = ''; fresh = true;
    show_();
}

function cmdBack_Click(e) {
    entry = entry.length > 1 ? entry.slice(0, -1) : '0';
    if (entry === '-') entry = '0';
    show_();
}

function cmdSign_Click(e) {
    entry = entry.startsWith('-') ? entry.slice(1) : (entry === '0' ? '0' : '-' + entry);
    show_();
}

function cmdPct_Click(e) { unary('%', (x) => (acc === null ? x / 100 : acc * x / 100)); }
function cmdSqrt_Click(e) { unary('sqrt', (x) => Math.sqrt(x)); }
function cmdSquare_Click(e) { unary('sqr', (x) => x * x); }

// ------------------------------------------------------------------ keyboard
function txtDisplay_KeyPress(e) {
    const key = keyName(e);
    const ch = e.KeyChar;
    if (/^[0-9.]$/.test(ch)) digit(ch);
    else if (ch && '+-*/'.includes(ch)) operator(ch);
    else if (ch === '=' || key === 'Return') equals();
    else if (ch === '%') cmdPct_Click(e);
    else if (key === 'BackSpace') cmdBack_Click(e);
    else if (key === 'Escape') cmdClear_Click(e);
    show_();       // the (read-only) TextBox always shows the calculator's value
}

/** Name of the key (Return, BackSpace, Escape ...): the 4th field of the event arguments is the Windows key
 *  code (13, 8, 27 ...). */
const KEY_NAMES = { 13: 'Return', 8: 'BackSpace', 27: 'Escape' };
function keyName(e) {
    const k = String(e.args || '').split(' ')[3] || '';
    return KEY_NAMES[k] || k;
}

// ------------------------------------------------------------------ menu
function mnuHistory_Click(e) {
    const visible = get('lstHistory', 'Visible') === 'True';
    set('lstHistory', 'Visible', !visible);
}

function mnuClearHistory_Click(e) { call('lstHistory', 'Clear'); }

function mnuKeys_Click(e) {
    msgbox('Type in the display: 0-9 . + - * / % , Enter or = to calculate, BackSpace, Esc to clear.');
}

function mnuAbout_Click(e) {
    msgbox('Calculator - a RAD IDE example in JavaScript. (c) 2026 Musoftware - https://musoftwares.com');
}

function lstHistory_DoubleClick(e) {
    const line = get('lstHistory', 'Text');            // "12 + 30 = 42"
    const i = line.lastIndexOf('= ');
    if (i >= 0) { entry = line.slice(i + 2); fresh = true; show_(); }
}

// ------------------------------------------------------------------ logic
function digit(d) {
    if (fresh) { entry = d === '.' ? '0.' : d; fresh = false; }
    else if (d === '.' && entry.includes('.')) return;
    else entry = entry === '0' && d !== '.' ? d : entry + d;
    show_();
}

function operator(o) {
    if (op && !fresh) equals(true);
    acc = Number(entry);
    op = o;
    fresh = true;
}

function equals(chained) {
    if (!op) return;
    const b = Number(entry);
    const r = calculate(acc, op, b);                    // CalcEngine.js
    call('lstHistory', 'AddItem', `${formatNumber(acc)} ${op} ${formatNumber(b)} = ${formatNumber(r)}`);
    entry = formatNumber(r);
    acc = chained ? r : null;
    op = chained ? op : '';
    fresh = true;
    show_();
}

function unary(name, f) {
    const x = Number(entry);
    const r = f(x);
    call('lstHistory', 'AddItem', `${name}(${formatNumber(x)}) = ${formatNumber(r)}`);
    entry = formatNumber(r);
    fresh = true;
    show_();
}

function show_() { set('txtDisplay', 'Text', entry); }
