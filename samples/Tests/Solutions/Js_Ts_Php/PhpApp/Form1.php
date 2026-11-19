<?php
function Form1_Load($e)
{
    echo 'P1 ', PyLib::Mul(3, 4), "\n";
    echo 'P2 ', PyLib_Hello('Pat'), "\n";
    echo 'P3 ', JsLib::Add(5, 5), ' ', JsLib::Greet('zed'), "\n";
    echo 'P4 ', TsLib::Square(9), "\n";
}
