# Class Library PsLib. Its functions are the library's public functions (names starting
# with _ stay private): a project that references PsLib (Add Reference) calls them natively -
#     PsLib.Add 2 3  or  $PsLib.Add(2, 3) in PowerShell,  PsLib.Add(2, 3) in C#/Python/Java
# Arguments and results are JSON values. Return a one-item list with: return ,@($x)

# Adds two numbers.
function Add($a, $b) {
    return $a + $b
}

# Returns a greeting.
function Greet($name) {
    return "Hello, $name!"
}
