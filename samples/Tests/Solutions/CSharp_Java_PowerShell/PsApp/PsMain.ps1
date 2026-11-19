function Run {
    $a = CsLib.Add 2 3
    $b = $CsLib.Greet("PS")
    $c = JLib.shout "ok"
    $d = $PyLib.Add(5, 6)
    $e = (JLib.pair 1 "x") -join ","
    $f = CsLib.Count @(1, 2, 3)
    return "$a|$b|$c|$d|$e|$f"
}
