// Event handlers for Form1 - written for the GUI Bridge (radgui.js). The native build runs the same code
// in a Node.js single executable (real V8 / Node APIs / npm packages) with the forms drawn by radforms.
const fs = require('fs');
const path = require('path');
const shout = require('rad-shout');          // an npm package (node_modules), bundled into the exe
const helpers = require('./Helpers');        // a module of this project (CommonJS)

let ticks = 0;

function Form1_Load(e) {
    fs.writeFileSync(path.join(process.cwd(), 'fs_check.txt'), 'fs ok', 'utf8');
    const back = fs.readFileSync(path.join(process.cwd(), 'fs_check.txt'), 'utf8');
    set('Form1', 'Text', `${shout.tag('Native JavaScript demo')} [${back}]`);
    set('lblOut', 'Caption', 'ready');
    ui.lstLog.AddItem('Form1 loaded');
}

function cmdAdd_Click(e) {
    const a = getNum('txtA', 'Text');
    const b = getNum('txtB', 'Text');
    set('lblOut', 'Caption', a + b);
    call('lstLog', 'AddItem', `${a} x ${b} = ${helpers.multiply(a, b)}`);
}

function txtA_TextChanged(e) {
    ui.lblEcho.Caption = ui.txtA.Text;
}

function chkBig_CheckedChanged(e) {
    const on = getNum('chkBig', 'Value') === 1;
    set('lblOut', 'FontSize', on ? 14 : 9);
    set('lblOut', 'Caption', on ? 'big' : 'small');
}

function optTwo_CheckedChanged(e) {
    set('lblEcho', 'Caption', get('optTwo', 'Value'));
}

function cboColor_SelectedIndexChanged(e) {
    set('lblOut', 'Caption', get('cboColor', 'Text'));
}

function tmrTick_Tick(e) {
    ticks++;
    set('lblTicks', 'Caption', ticks);
    set('prgTicks', 'Value', ticks % 51);
}

function cmdShow2_Click(e) { show('Form2'); }

function mnuForm2_Click(e) { show('Form2'); }

function mnuAbout_Click(e) { msgbox('RAD IDE native JavaScript demo'); }

function mnuExit_Click(e) { end(); }

function cmdMsg_Click(e) {
    msgbox('Hello from radforms');
    set('lblOut', 'Caption', 'msg done');
}

function cmdArabic_Click(e) {
    set('lblOut', 'Caption', 'مرحبا بالعالم');
}
