<?php
// Upper-case a text
function Shout($s) { return strtoupper($s) . '!'; }
function Add($a, $b) { return $a + $b; }
function Info(): array { return ['lang' => 'php', 'ver' => PHP_MAJOR_VERSION]; }
function _secret() { return 1; }
