// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a small text editor written in JavaScript (Node.js) with a RAD IDE form.
// Shows: a MenuStrip with File / Edit / Format / Help, a multi-line TextBox, Open / Save dialogs
// (OpenFileDialog / SaveFileDialog components), Node's fs module, InputBox / MsgBox, the form caption,
// and settings kept in a JSON file (the last opened file comes back on the next start).
// Text helpers (statistics, find, case) live in the module TextUtils.js.

const fs = require('fs');
const path = require('path');

const SETTINGS = path.join(__radfolder, 'notepad.settings.json');
let currentFile = '';     // full path of the file being edited ('' = Untitled)
let savedText = '';       // text at the last open/save, to know if there are unsaved changes

function Form1_Load(e) {
    const s = loadSettings();
    if (s.lastFile && fs.existsSync(s.lastFile)) {
        openFile(s.lastFile);
    } else {
        newDocument();
    }
}

// ------------------------------------------------------------------ File menu
function mnuNew_Click(e) {
    if (!confirmDiscard()) return;
    newDocument();
}

function mnuOpen_Click(e) {
    if (!confirmDiscard()) return;
    if (call('dlgOpen', 'ShowDialog') !== 'OK') return;      // the user pressed Cancel
    openFile(get('dlgOpen', 'FileName'));
}

function mnuSave_Click(e) {
    if (currentFile) saveFile(currentFile);
    else mnuSaveAs_Click(e);
}

function mnuSaveAs_Click(e) {
    set('dlgSave', 'FileName', currentFile || 'Untitled.txt');
    if (call('dlgSave', 'ShowDialog') !== 'OK') return;
    saveFile(get('dlgSave', 'FileName'));
}

function mnuExit_Click(e) {
    if (confirmDiscard()) end();
}

// ------------------------------------------------------------------ Edit menu
function mnuFind_Click(e) {
    const what = input('Find what?');
    if (!what) return;
    const hits = countOccurrences(get('txtDoc', 'Text'), what);    // TextUtils.js
    status(hits ? `"${what}" found ${hits} time(s)` : `"${what}" not found`);
    msgbox(hits ? `"${what}" occurs ${hits} time(s).` : `Cannot find "${what}".`);
}

function mnuReplace_Click(e) {
    const what = input('Replace what?');
    if (!what) return;
    const by = input(`Replace "${what}" with:`);
    const text = get('txtDoc', 'Text');
    const n = countOccurrences(text, what);
    set('txtDoc', 'Text', text.split(what).join(by));
    status(`${n} replacement(s)`);
}

function mnuDate_Click(e) {
    const stamp = new Date().toLocaleString();
    set('txtDoc', 'Text', get('txtDoc', 'Text') + stamp);
    status('Inserted ' + stamp);
}

// ------------------------------------------------------------------ Format menu
function mnuUpper_Click(e) { set('txtDoc', 'Text', get('txtDoc', 'Text').toUpperCase()); }
function mnuLower_Click(e) { set('txtDoc', 'Text', get('txtDoc', 'Text').toLowerCase()); }
function mnuSort_Click(e) { set('txtDoc', 'Text', sortLines(get('txtDoc', 'Text'))); }

// ------------------------------------------------------------------ Help menu
function mnuStats_Click(e) {
    const s = textStats(get('txtDoc', 'Text'));
    msgbox(`Lines: ${s.lines}   Words: ${s.words}   Characters: ${s.chars}`);
    status(`${s.words} words`);
}

function mnuAbout_Click(e) {
    msgbox('Notepad - a RAD IDE example in JavaScript (Node.js ' + process.version + ').\n' +
           '(c) 2026 Musoftware - https://musoftwares.com - MIT License');
}

function txtDoc_KeyUp(e) {
    status((currentFile ? path.basename(currentFile) : 'Untitled') + (isDirty() ? ' (modified)' : ''));
}

// ------------------------------------------------------------------ helpers
function newDocument() {
    currentFile = '';
    savedText = '';
    set('txtDoc', 'Text', '');
    updateTitle();
    status('New document');
}

function openFile(file) {
    try {
        const text = fs.readFileSync(file, 'utf8').replace(/^﻿/, '');
        set('txtDoc', 'Text', text);
        currentFile = file;
        savedText = text;
        updateTitle();
        rememberFile(file);
        status(`Opened ${path.basename(file)} (${text.length} characters)`);
    } catch (err) {
        msgbox('Cannot open the file:\n' + err.message);
    }
}

function saveFile(file) {
    try {
        const text = get('txtDoc', 'Text');
        fs.writeFileSync(file, text, 'utf8');
        currentFile = file;
        savedText = text;
        updateTitle();
        rememberFile(file);
        status(`Saved ${path.basename(file)}`);
    } catch (err) {
        msgbox('Cannot save the file:\n' + err.message);
    }
}

function isDirty() { return get('txtDoc', 'Text') !== savedText; }

function confirmDiscard() {
    if (!isDirty()) return true;
    const answer = input('The text has changed. Type YES to discard the changes:');
    return answer.trim().toUpperCase() === 'YES';
}

function updateTitle() {
    set('Form1', 'Caption', (currentFile ? path.basename(currentFile) : 'Untitled') + ' - Notepad (JavaScript)');
}

function status(text) { set('lblStatus', 'Caption', text); }

function loadSettings() {
    try { return JSON.parse(fs.readFileSync(SETTINGS, 'utf8')); } catch (err) { return {}; }
}

function rememberFile(file) {
    const s = loadSettings();
    s.lastFile = file;
    try { fs.writeFileSync(SETTINGS, JSON.stringify(s, null, 2)); } catch (err) { /* read-only folder */ }
}
