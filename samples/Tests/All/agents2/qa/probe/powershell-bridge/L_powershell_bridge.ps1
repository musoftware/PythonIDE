# Class Library L_powershell_bridge. Its functions are the library's public functions (names starting
# with _ stay private): a project that references L_powershell_bridge (Add Reference) calls them natively -
#     L_powershell_bridge.Add 2 3  or  $L_powershell_bridge.Add(2, 3) in PowerShell,  L_powershell_bridge.Add(2, 3) in C#/Python/Java
# Arguments and results are JSON values. Return a one-item list with: return ,@($x)

# Adds two numbers.
function Add($a, $b) {
    return $a + $b
}

# Returns a greeting.
function Greet($name) {
    return "Hello, $name!"
}
