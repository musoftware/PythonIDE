<?php
// Class Library module L_php. Every top-level function here is public: a project that
// references this library calls it as native code, e.g. L_php.Add(2, 3) in Python/C#/JS,
// L_php::Add(2, 3) or L_php_Add(2, 3) in PHP. Names starting with _ stay private.
// Arguments and results are JSON values (number, string, bool, null, array).

/** Add two numbers and return the sum. */
function Add($a, $b)
{
    return $a + $b;
}

/** Say hello to someone. */
function Greet($name)
{
    return "Hello, $name!";
}
