# Debugger test (PowerShell): breakpoint on the "$text = ..." line of cmdGreet_Click, then F5 and Greet.
$script:clicks = 0

function Make-Greeting([string]$Name, [int]$N) {
    $text = "Hello, $Name! (click $N)"
    return $text
}

function Form1_Load($e) {
    $lblOut.Text = "Press Greet."
}

function cmdGreet_Click($e) {
    $name = $txtName.Text
    $script:clicks++
    $info = @{ name = $name; clicks = $script:clicks }
    $text = Make-Greeting -Name $name -N $script:clicks
    $lblOut.Text = $text
}
