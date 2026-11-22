// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Handlers of the modal Settings form (opened by Form1 with call("Settings", "ShowDialog")).
// The two forms run in the same Node.js program, so OK can call applySettings() of Form1.js directly.

function Settings_Load(e) {
}

function cmdOK_Click(e) {
    applySettings({
        focus: getNum('Settings.numFocus', 'Value'),
        break: getNum('Settings.numBreak', 'Value'),
        arabic: get('Settings.chkArabic', 'Value') === '1',
        notify: get('Settings.chkBeep', 'Value') === '1',
    });
    hide('Settings');
}

function cmdCancel_Click(e) {
    hide('Settings');
}
