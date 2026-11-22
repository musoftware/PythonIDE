<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Text Tools - string utilities in PHP with a RAD IDE form.
// Shows: multi-line TextBoxes (input / read-only output), a ComboBox of operations, a CheckBox that runs
// the operation while you type (TextChanged), menus with sample texts (English and Arabic), and PHP's
// multibyte string functions (mb_*), so Arabic text is reversed, counted and cased correctly.
// The operations are in TextOps.php.

function Form1_Load($e)
{
    rad_set('cboOp', 'ListIndex', 0);
    stats();
}

function cmdRun_Click($e) { run(); }
function mnuRun_Click($e) { run(); }
function cboOp_SelectedIndexChanged($e) { run(); }

function txtInput_TextChanged($e)
{
    if (rad_get('chkAuto', 'Value') === '1') {
        run();
    }
    stats();
}

function mnuSwap_Click($e)
{
    rad_set('txtInput', 'Text', rad_get('txtOutput', 'Text'));
    rad_set('txtOutput', 'Text', '');
    stats();
}

function mnuSampleEn_Click($e)
{
    rad_set('txtInput', 'Text', "The quick brown fox\njumps over   the lazy dog.\nThe end");
    stats();
}

function mnuSampleAr_Click($e)
{
    rad_set('txtInput', 'Text', "مرحبا بكم في بيئة التطوير\nالبرمجة بلغة PHP سهلة");
    stats();
}

function mnuExit_Click($e) { rad_end(); }

// ------------------------------------------------------------------ helpers
function run()
{
    $op = rad_get('cboOp', 'Text');
    $in = str_replace("\r\n", "\n", rad_get('txtInput', 'Text'));
    try {
        $out = apply_op($op, $in);                // TextOps.php
    } catch (InvalidArgumentException $ex) {
        $out = '';
        rad_msgbox($ex->getMessage());
    }
    rad_set('txtOutput', 'Text', str_replace("\n", "\r\n", $out));
}

function stats()
{
    $s = text_stats(str_replace("\r\n", "\n", rad_get('txtInput', 'Text')));
    rad_set('lblStats', 'Caption', sprintf('%d characters, %d words, %d lines, %d bytes (UTF-8)',
        $s['chars'], $s['words'], $s['lines'], $s['bytes']));
}
