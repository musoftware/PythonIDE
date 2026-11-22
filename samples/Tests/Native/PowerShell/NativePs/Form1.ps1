# Event handlers for Form1 (native build test).
$script:ticks = 0

function Form1_Load($e) {
    $lblOut.Text = "Loaded"
}

function btnGreet_Click($e) {
    $name = $txtName.Text
    if ($chkShout.Value -eq "1") { $text = radcall "Helper.Shout" $name } else { $text = Greet $name }
    $lblOut.Text = $text
    $lstLog.AddItem($text)
    $lblCount.Text = "$($lstLog.ListCount) items"
}

function txtName_TextChanged($e) {
    $lblEcho.Text = "echo:" + $txtName.Text
}

function btnStart_Click($e) {
    $script:ticks = 0
    $tmrTick.Enabled = $true
}

function tmrTick_Tick($e) {
    $script:ticks++
    $lblTicks.Text = "$script:ticks"
    if ($script:ticks -ge 5) { $tmrTick.Enabled = $false }
}

function btnForm2_Click($e) {
    RadShow Form2
}

function mnuFileHello_Click($e) {
    $lblOut.Text = "Menu clicked"
}

function mnuFileExit_Click($e) { RadEnd }

function btnClose_Click($e) { RadEnd }
