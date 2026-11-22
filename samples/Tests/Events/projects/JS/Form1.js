// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
const fs = require('fs');

let closing = 0;

function evlog(name, rest) {
    const p = process.env.RADEVT_LOG;
    if (!p) return;
    fs.appendFileSync(p, `EVT ${name}${rest ? ' ' + rest : ''}\n`, 'utf8');
}

function Form1_Load(e) {
    evlog('Form1_Load', '');
}

function Form1_Activated(e) {
    evlog('Form1_Activated', '');
}

function Form1_FormClosed(e) {
    evlog('Form1_FormClosed', '');
}

function cmdA_MouseDown(e) {
    evlog('cmdA_MouseDown', e ? e.args : '');
}

function cmdA_MouseUp(e) {
    evlog('cmdA_MouseUp', e ? e.args : '');
}

function cmdA_Click(e) {
    evlog('cmdA_Click', '');
}

function lblA_MouseDown(e) {
    evlog('lblA_MouseDown', e ? e.args : '');
}

function lblA_MouseUp(e) {
    evlog('lblA_MouseUp', e ? e.args : '');
}

function lblA_Click(e) {
    evlog('lblA_Click', '');
}

function txtA_GotFocus(e) {
    evlog('txtA_GotFocus', '');
}

function txtA_LostFocus(e) {
    evlog('txtA_LostFocus', '');
}

function txtA_KeyDown(e) {
    evlog('txtA_KeyDown', e ? e.args : '');
}

function txtA_KeyPress(e) {
    evlog('txtA_KeyPress', e ? e.args : '');
}

function txtA_KeyUp(e) {
    evlog('txtA_KeyUp', e ? e.args : '');
}

function txtA_TextChanged(e) {
    evlog('txtA_TextChanged', 'text=' + get('txtA', 'Text'));
}

function txtB_GotFocus(e) {
    evlog('txtB_GotFocus', '');
}

function txtB_LostFocus(e) {
    evlog('txtB_LostFocus', '');
}

function chkA_CheckedChanged(e) {
    evlog('chkA_CheckedChanged', 'value=' + get('chkA', 'Value'));
}

function lstA_SelectedIndexChanged(e) {
    evlog('lstA_SelectedIndexChanged', 'index=' + get('lstA', 'ListIndex'));
}

function Form1_FormClosing(e) {
    closing++;
    evlog('Form1_FormClosing', '');
    if (closing === 1) set('Form1', 'Cancel', 'True');
}

function cmdCode_Click(e) {
    evlog('cmdCode_Click', 'begin');
    set('txtA', 'Text', 'code');
    set('chkA', 'Value', 1);
    set('lstA', 'ListIndex', 2);
    evlog('cmdCode_Click', 'end');
}

function cmdTmr_Click(e) {
    evlog('cmdTmr_Click', '');
    set('tmrA', 'Enabled', 'True');
}

function tmrA_Tick(e) {
    set('tmrA', 'Enabled', 'False');
    evlog('tmrA_Tick', '');
}
