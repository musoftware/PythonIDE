// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Focus Timer - a "Pomodoro" timer in JavaScript with two RAD IDE forms.
// Shows: a Timer component (Tick every second), a ProgressBar, a modal second form (Settings, opened with
// call("Settings", "ShowDialog")) whose OK / Cancel handlers live in Settings.js, settings saved to a JSON
// file and loaded on start, and an Arabic interface (all captions switch to Arabic text).

const fs = require('fs');
const path = require('path');

const SETTINGS_FILE = path.join(__radfolder, 'focustimer.settings.json');
const TEXT = {
    en: { focus: 'Focus', break: 'Break', start: 'Start', pause: 'Pause', reset: 'Reset', settings: 'Settings...',
          done: 'period finished', title: 'Focus Timer - JavaScript' },
    ar: { focus: 'تركيز', break: 'استراحة', start: 'ابدأ', pause: 'إيقاف مؤقت', reset: 'إعادة', settings: 'الإعدادات...',
          done: 'انتهت الفترة', title: 'مؤقت التركيز - جافاسكربت' },
};

let cfg = { focus: 25, break: 5, arabic: false, notify: true };
let mode = 'focus';        // 'focus' or 'break'
let left = 0;              // seconds left in this period
let running = false;
let finished = 0;          // focus periods finished

function Form1_Load(e) {
    cfg = Object.assign(cfg, readSettings());
    applyLanguage();
    resetPeriod();
}

// ------------------------------------------------------------------ buttons / menu
function cmdStart_Click(e) {
    running = !running;
    set('tmrTick', 'Enabled', running);
    set('cmdStart', 'Caption', running ? t().pause : t().start);
}

function cmdReset_Click(e) {
    running = false;
    set('tmrTick', 'Enabled', false);
    set('cmdStart', 'Caption', t().start);
    mode = 'focus';
    resetPeriod();
}

function cmdSettings_Click(e) {
    // fill the dialog with the current settings, then show it modally; Settings.js applies OK / Cancel
    set('Settings.numFocus', 'Value', cfg.focus);
    set('Settings.numBreak', 'Value', cfg.break);
    set('Settings.chkArabic', 'Value', cfg.arabic ? 1 : 0);
    set('Settings.chkBeep', 'Value', cfg.notify ? 1 : 0);
    call('Settings', 'ShowDialog');
}

function mnuStart_Click(e) { cmdStart_Click(e); }
function mnuReset_Click(e) { cmdReset_Click(e); }
function mnuSettings_Click(e) { cmdSettings_Click(e); }
function mnuExit_Click(e) { end(); }

// ------------------------------------------------------------------ timer
function tmrTick_Tick(e) {
    if (!running) return;
    left -= 1;
    if (left <= 0) {
        log(`${t()[mode]} - ${t().done} (${new Date().toLocaleTimeString()})`);
        if (mode === 'focus') finished += 1;
        mode = mode === 'focus' ? 'break' : 'focus';
        resetPeriod();
        if (cfg.notify) msgbox(`${t()[mode]}!`);
        return;
    }
    showTime();
}

// ------------------------------------------------------------------ called by Settings.js
/** The user pressed OK in the Settings dialog. */
function applySettings(newCfg) {
    cfg = Object.assign(cfg, newCfg);
    writeSettings(cfg);
    applyLanguage();
    if (!running) resetPeriod();
}

// ------------------------------------------------------------------ helpers
function t() { return cfg.arabic ? TEXT.ar : TEXT.en; }

function resetPeriod() {
    left = (mode === 'focus' ? cfg.focus : cfg.break) * 60;
    set('prgTime', 'Max', left);
    set('lblMode', 'Caption', `${t()[mode]}  #${finished + 1}`);
    showTime();
}

function showTime() {
    const m = Math.floor(left / 60), s = left % 60;
    set('lblTime', 'Caption', `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    set('prgTime', 'Value', Number(get('prgTime', 'Max')) - left);
}

function applyLanguage() {
    const x = t();
    set('Form1', 'Caption', x.title);
    set('cmdStart', 'Caption', running ? x.pause : x.start);
    set('cmdReset', 'Caption', x.reset);
    set('cmdSettings', 'Caption', x.settings);
    set('lblMode', 'Caption', `${x[mode]}  #${finished + 1}`);
}

function log(text) { call('lstLog', 'AddItem', text); }

function readSettings() {
    try { return JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8')); } catch (err) { return {}; }
}

function writeSettings(c) {
    try { fs.writeFileSync(SETTINGS_FILE, JSON.stringify(c, null, 2), 'utf8'); } catch (err) { /* read-only */ }
}
