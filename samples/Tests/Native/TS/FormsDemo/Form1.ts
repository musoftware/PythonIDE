// Event handlers for Form1 (TypeScript). Like in the IDE the types are stripped (Node's type stripper); the
// native build does that at build time and runs the result in a Node.js single executable.
const fs = require('fs');
const shout = require('rad-shout');          // an npm package (node_modules), bundled into the exe
const helpers = require('./Helpers');        // a module of this project (CommonJS)

interface Sum { a: number; b: number; }
enum Size { Small = 9, Big = 14 }

let ticks: number = 0;

function Form1_Load(e: RadEvent): void {
    fs.writeFileSync('fs_check.txt', 'fs ok', 'utf8');
    const back: string = fs.readFileSync('fs_check.txt', 'utf8');
    set('Form1', 'Text', `${shout.tag('Native TypeScript demo')} [${back}]`);
    set('lblOut', 'Caption', 'ready');
    ui.lstLog.AddItem('Form1 loaded');
}

function cmdAdd_Click(e: RadEvent): void {
    const s: Sum = { a: getNum('txtA', 'Text'), b: getNum('txtB', 'Text') };
    set('lblOut', 'Caption', s.a + s.b);
    call('lstLog', 'AddItem', `${s.a} x ${s.b} = ${helpers.multiply(s.a, s.b)}`);
}

function txtA_TextChanged(e: RadEvent): void {
    ui.lblEcho.Caption = ui.txtA.Text;
}

function chkBig_CheckedChanged(e: RadEvent): void {
    const on: boolean = getNum('chkBig', 'Value') === 1;
    set('lblOut', 'FontSize', on ? Size.Big : Size.Small);
    set('lblOut', 'Caption', on ? 'big' : 'small');
}

function optTwo_CheckedChanged(e: RadEvent): void {
    set('lblEcho', 'Caption', get('optTwo', 'Value'));
}

function cboColor_SelectedIndexChanged(e: RadEvent): void {
    set('lblOut', 'Caption', get('cboColor', 'Text'));
}

function tmrTick_Tick(e: RadEvent): void {
    ticks++;
    set('lblTicks', 'Caption', ticks);
    set('prgTicks', 'Value', ticks % 51);
}

function cmdShow2_Click(e: RadEvent): void { show('Form2'); }

function mnuForm2_Click(e: RadEvent): void { show('Form2'); }

function mnuAbout_Click(e: RadEvent): void { msgbox('RAD IDE native TypeScript demo'); }

function mnuExit_Click(e: RadEvent): void { end(); }

function cmdMsg_Click(e: RadEvent): void {
    msgbox('Hello from radforms');
    set('lblOut', 'Caption', 'msg done');
}

function cmdArabic_Click(e: RadEvent): void {
    set('lblOut', 'Caption', 'مرحبا بالعالم');
}
