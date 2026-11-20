<?php
function add($a, $b) { return $a + $b; }
function viaTs($a) { return radcall('CalcT.viaJs', $a); }
function reenter($x) { return radcall('CalcP.add', $x, 100); }
function gui() { return rad_get('txtA', 'Text'); }
