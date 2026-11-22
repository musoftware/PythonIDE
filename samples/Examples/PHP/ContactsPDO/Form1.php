<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts (PDO) - a desktop address book in PHP with a SQLite database through PDO.
// Shows: PDO with prepared statements (Db.php), a ListBox master list with the record ids kept in PHP,
// a detail panel with a multi-line Notes box, live search (TextChanged), insert / update in one Save
// button, delete after an InputBox confirmation, and UTF-8 Arabic text stored and searched.

$GLOBALS['ids'] = [];        // ListBox line -> contact id
$GLOBALS['current'] = 0;     // id shown in the detail panel (0 = new)

function Form1_Load($e)
{
    db_open(getcwd() . DIRECTORY_SEPARATOR . 'contacts.sqlite');      // Db.php
    if (db_count() === 0) {                                          // first start: a few sample rows
        db_save(0, ['name' => 'Omar Hassan', 'phone' => '012 345 6789', 'city' => 'Cairo', 'notes' => 'Customer since 2020']);
        db_save(0, ['name' => 'ليلى محمود', 'phone' => '010 987 6543', 'city' => 'الإسكندرية', 'notes' => "سطر أول\nسطر ثان"]);
    }
    fillList();
    clearDetail();
}

function txtSearch_TextChanged($e) { fillList(); }

function lstContacts_SelectedIndexChanged($e)
{
    $i = (int)rad_num('lstContacts', 'ListIndex');
    if ($i < 0 || !isset($GLOBALS['ids'][$i])) {
        return;
    }
    $c = db_get($GLOBALS['ids'][$i]);
    if (!$c) {
        return;
    }
    $GLOBALS['current'] = (int)$c['id'];
    foreach (['name', 'phone', 'city', 'notes'] as $f) {
        rad_set('txt' . ucfirst($f), 'Text', $c[$f]);
    }
    rad_set('lblInfo', 'Caption', 'Contact #' . $c['id'] . ', added ' . $c['created']);
}

function cmdSave_Click($e)
{
    $data = [];
    foreach (['name', 'phone', 'city', 'notes'] as $f) {
        $data[$f] = trim(rad_get('txt' . ucfirst($f), 'Text'));
    }
    if ($data['name'] === '') {
        rad_msgbox('The name is required.');
        return;
    }
    $isNew = $GLOBALS['current'] === 0;
    $GLOBALS['current'] = db_save($GLOBALS['current'], $data);
    fillList();
    rad_set('lblInfo', 'Caption', ($isNew ? 'Added' : 'Saved') . ' contact #' . $GLOBALS['current']);
}

function cmdNew_Click($e) { clearDetail(); }

function cmdDelete_Click($e)
{
    if ($GLOBALS['current'] === 0) {
        rad_msgbox('Select a contact first.');
        return;
    }
    if (strtoupper(trim(rad_input('Delete this contact? Type YES to confirm:'))) !== 'YES') {
        return;
    }
    db_delete($GLOBALS['current']);
    clearDetail();
    fillList();
}

function mnuExit_Click($e) { rad_end(); }

function mnuAbout_Click($e)
{
    rad_msgbox('Contacts - a RAD IDE example: PHP ' . PHP_VERSION . ' + PDO SQLite. (c) 2026 Musoftware');
}

// ------------------------------------------------------------------ helpers
function fillList()
{
    $rows = db_find(rad_get('txtSearch', 'Text'));
    rad_call('lstContacts', 'Clear');
    $GLOBALS['ids'] = [];
    foreach ($rows as $r) {
        rad_call('lstContacts', 'AddItem', $r['name'] . ($r['city'] !== '' ? ' (' . $r['city'] . ')' : ''));
        $GLOBALS['ids'][] = (int)$r['id'];
    }
}

function clearDetail()
{
    $GLOBALS['current'] = 0;
    foreach (['txtName', 'txtPhone', 'txtCity', 'txtNotes'] as $t) {
        rad_set($t, 'Text', '');
    }
    rad_set('lblInfo', 'Caption', db_count() . ' contact(s) in the database');
}
