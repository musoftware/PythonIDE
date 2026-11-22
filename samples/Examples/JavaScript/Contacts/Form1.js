// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in JavaScript with a SQLite database (Node's built-in node:sqlite, no npm
// package needed; Node.js 22.5+). Shows: CRUD (add / update / delete), a DataGridView filled from a
// query, live search (TextChanged), a ComboBox, selecting a grid row to edit it, validation with MsgBox,
// a confirmation InputBox, CSV export with fs, and Arabic text stored and searched in the database.
// The database code is in the module ContactsDb.js; the database file is contacts.db in the project folder.

const fs = require('fs');
const path = require('path');

let selectedId = 0;       // id of the contact shown in the text boxes (0 = a new one)

function Form1_Load(e) {
    openDatabase(path.join(__radfolder, 'contacts.db'));       // ContactsDb.js
    set('cboGroup', 'Text', 'Friends');
    refresh();
}

// ------------------------------------------------------------------ buttons
function cmdAdd_Click(e) {
    const c = readForm();
    if (!c) return;
    selectedId = addContact(c);
    refresh();
    status(`Added "${c.name}"`);
}

function cmdUpdate_Click(e) {
    if (!selectedId) { msgbox('Click a row in the list first.'); return; }
    const c = readForm();
    if (!c) return;
    updateContact(selectedId, c);
    refresh();
    status(`Updated "${c.name}"`);
}

function cmdDelete_Click(e) {
    if (!selectedId) { msgbox('Click a row in the list first.'); return; }
    const name = get('txtName', 'Text');
    if (input(`Delete "${name}"? Type YES to confirm:`).trim().toUpperCase() !== 'YES') return;
    deleteContact(selectedId);
    clearForm();
    refresh();
    status(`Deleted "${name}"`);
}

function cmdNew_Click(e) { clearForm(); }

function txtSearch_TextChanged(e) { refresh(); }

/** A row was clicked: show that contact in the text boxes. */
function grdContacts_SelectedIndexChanged(e) {
    const row = Number(get('grdContacts', 'Row'));
    if (row < 1) return;
    const id = Number(call('grdContacts', 'TextMatrix', row, 0));
    const c = getContact(id);
    if (!c) return;
    selectedId = id;
    set('txtName', 'Text', c.name);
    set('txtPhone', 'Text', c.phone);
    set('txtEmail', 'Text', c.email);
    set('cboGroup', 'Text', c.grp);
    status(`Editing #${id}`);
}

// ------------------------------------------------------------------ menu
function mnuExport_Click(e) {
    const file = path.join(__radfolder, 'contacts.csv');
    const rows = findContacts('');
    const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const csv = ['Id,Name,Phone,Email,Group']
        .concat(rows.map((r) => [r.id, q(r.name), q(r.phone), q(r.email), q(r.grp)].join(',')));
    fs.writeFileSync(file, '﻿' + csv.join('\r\n'), 'utf8');      // BOM: Excel opens Arabic correctly
    msgbox(`${rows.length} contact(s) exported to ${file}`);
}

function mnuSamples_Click(e) {
    [['Sara Ahmed', '010 1234 5678', 'sara@example.com', 'Work'],
     ['محمد علي', '011 2222 3333', 'mohamed@example.com', 'Family'],
     ['John Smith', '+1 555 0100', 'john@example.com', 'Friends']]
        .forEach(([name, phone, email, grp]) => addContact({ name, phone, email, grp }));
    refresh();
}

function mnuExit_Click(e) { end(); }

function mnuAbout_Click(e) {
    msgbox('Contacts - a RAD IDE example: JavaScript + SQLite (node:sqlite). (c) 2026 Musoftware');
}

// ------------------------------------------------------------------ helpers
function readForm() {
    const c = {
        name: get('txtName', 'Text').trim(),
        phone: get('txtPhone', 'Text').trim(),
        email: get('txtEmail', 'Text').trim(),
        grp: get('cboGroup', 'Text') || 'Other',
    };
    if (!c.name) { msgbox('Please type a name.'); return null; }
    if (c.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(c.email)) { msgbox('The email address is not valid.'); return null; }
    return c;
}

function clearForm() {
    selectedId = 0;
    for (const t of ['txtName', 'txtPhone', 'txtEmail']) set(t, 'Text', '');
    status('New contact');
}

function refresh() {
    const rows = findContacts(get('txtSearch', 'Text'));
    call('grdContacts', 'Clear');
    for (const r of rows) call('grdContacts', 'AddItem', r.id, r.name, r.phone, r.email, r.grp);
    set('lblCount', 'Caption', `${rows.length} of ${countContacts()} contact(s)`);
}

function status(text) { set('lblHint', 'Caption', text); }
