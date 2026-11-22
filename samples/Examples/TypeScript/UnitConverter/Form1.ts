// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Unit Converter - TypeScript with a RAD IDE form (GUI Bridge, Node.js strips the types when it runs).
// Shows: RadioButtons in a GroupBox choosing the quantity, two ComboBoxes filled from code, live
// conversion while typing (TextChanged) and on SelectedIndexChanged, a TrackBar for the decimals,
// typed data (the Units.ts module: interfaces, a union type, a Record) and a log ListBox.

let kind: Quantity = 'length';

function Form1_Load(e: RadEvent): void {
    fillUnits();
}

// ------------------------------------------------------------------ quantity
function optLength_CheckedChanged(e: RadEvent): void { choose('length', 'optLength'); }
function optMass_CheckedChanged(e: RadEvent): void { choose('mass', 'optMass'); }
function optTemp_CheckedChanged(e: RadEvent): void { choose('temperature', 'optTemp'); }
function optData_CheckedChanged(e: RadEvent): void { choose('data', 'optData'); }

function choose(q: Quantity, option: string): void {
    if (get(option, 'Value') !== 'True' || kind === q) return;     // only the option that became checked
    kind = q;
    fillUnits();
}

// ------------------------------------------------------------------ conversion
function txtValue_TextChanged(e: RadEvent): void { convertNow(); }
function cboFrom_SelectedIndexChanged(e: RadEvent): void { convertNow(); }
function cboTo_SelectedIndexChanged(e: RadEvent): void { convertNow(); }
function trkDecimals_ValueChanged(e: RadEvent): void { convertNow(); }

function cmdSwap_Click(e: RadEvent): void {
    const from = get('cboFrom', 'Text');
    set('cboFrom', 'Text', get('cboTo', 'Text'));
    set('cboTo', 'Text', from);
    convertNow();
}

function mnuLog_Click(e: RadEvent): void {
    const r = get('lblResult', 'Caption');
    if (r) call('lstLog', 'AddItem', r);
}

function mnuExit_Click(e: RadEvent): void { end(); }

function mnuAbout_Click(e: RadEvent): void {
    msgbox('Unit Converter - a RAD IDE example in TypeScript. (c) 2026 Musoftware - https://musoftwares.com');
}

// ------------------------------------------------------------------ helpers
function fillUnits(): void {
    const names: string[] = unitsOf(kind).map((u: Unit) => u.name);
    for (const box of ['cboFrom', 'cboTo']) {
        call(box, 'Clear');
        for (const n of names) call(box, 'AddItem', n);
    }
    set('cboFrom', 'ListIndex', 0);
    set('cboTo', 'ListIndex', Math.min(1, names.length - 1));
    convertNow();
}

function convertNow(): void {
    const text: string = get('txtValue', 'Text').trim().replace(',', '.');
    const value = Number(text);
    if (text === '' || !Number.isFinite(value)) {
        set('lblResult', 'Caption', text === '' ? '' : 'Not a number');
        return;
    }
    const from: string = get('cboFrom', 'Text');
    const to: string = get('cboTo', 'Text');
    const decimals: number = getNum('trkDecimals', 'Value');
    const result: number = convert(kind, value, from, to);          // Units.ts
    set('lblResult', 'Caption', `${value} ${from} = ${result.toFixed(decimals)} ${to}`);
}
