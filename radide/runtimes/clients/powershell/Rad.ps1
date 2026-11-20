# RAD IDE - GUI Bridge client for PowerShell (copied into _build/<lang> when the program runs - do not edit this copy).
#
#   MsgBox "text"                  InputBox "prompt"            RadEnd
#   RadSet obj prop value          RadGet obj prop              RadInvoke obj method arg1 arg2 ...
#   RadShow Form2 / RadHide Form2
#   radcall "Module.function" arg1 arg2   - call a function of any project module (any language)
# Controls are objects made in <Form>_designer.ps1:  $lblOut.Text = "Hi";  $lstLog.AddItem("x");  $txtIn.Text

$script:RadUtf8 = New-Object System.Text.UTF8Encoding $false
try { [Console]::OutputEncoding = $script:RadUtf8 } catch { }
$script:RadIn = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), $script:RadUtf8)
$script:RadOut = New-Object System.IO.StreamWriter([Console]::OpenStandardOutput(), $script:RadUtf8)
$script:RadOut.AutoFlush = $true
$script:RadHub = $null

function RadStr($Value) {
    if ($null -eq $Value) { return "" }
    if ($Value -is [bool]) { if ($Value) { return "True" } else { return "False" } }
    if ($Value -is [System.IFormattable]) { $s = $Value.ToString($null, [System.Globalization.CultureInfo]::InvariantCulture) }
    else { $s = "$Value" }
    return ($s -replace "`r`n", " " -replace "[`r`n]", " ")
}

function RadSend([string]$Line) {
    $script:RadOut.Write($Line + "`n")
    $script:RadOut.Flush()
}

function RadReadLine { return $script:RadIn.ReadLine() }

function RadAsk([string]$Line) {
    RadSend $Line
    $answer = $script:RadIn.ReadLine()
    if ($null -eq $answer) { [Environment]::Exit(0) }   # the IDE closed the program
    return $answer
}

function RadToNumber($Text) {
    $d = 0.0
    if ([double]::TryParse("$Text", [System.Globalization.NumberStyles]::Float,
            [System.Globalization.CultureInfo]::InvariantCulture, [ref]$d)) { return $d }
    return 0.0
}

function RadToBool($Text) { return ("$Text" -eq "True" -or "$Text" -eq "1" -or "$Text" -eq "-1") }

# ---------------------------------------------------------------- GUI
function RadSet([string]$Object, [string]$Property, $Value) { RadSend "SET $Object $Property $(RadStr $Value)" }
function RadGet([string]$Object, [string]$Property) {
    # stopped in a debugger (PSES lists every variable's properties): asking the IDE now would read the next
    # event line from stdin as the answer - the value is not read while paused
    if ($null -ne $PSDebugContext) { return "<${Object}.${Property} not read while paused>" }
    return RadAsk "GET $Object $Property"
}
function RadInvoke([string]$Object, [string]$Method) {
    $line = "CALL $Object $Method"
    if ($args.Count -gt 0) { $line += " " + (($args | ForEach-Object { RadStr $_ }) -join "`t") }
    return RadAsk $line
}
function MsgBox($Text) { return [int](RadToNumber (RadAsk "MSGBOX $(RadStr $Text)")) }
function InputBox($Prompt) { return RadAsk "INPUT $(RadStr $Prompt)" }
function RadShow([string]$Form) { RadSend "SHOW $Form" }
function RadHide([string]$Form) { RadSend "HIDE $Form" }
function RadEnd { RadSend "END"; [Environment]::Exit(0) }

# A control (or form) object with VB-style properties: Text Caption Value Enabled Visible Left Top Width Height
# BackColor ForeColor ListIndex ListCount Interval, and methods AddItem RemoveItem Clear List SetFocus Move ShowDialog.
function New-RadControl([string]$Path) {
    $o = New-Object PSObject
    $o | Add-Member -MemberType NoteProperty -Name Path -Value $Path
    foreach ($p in "Text", "Caption", "Value", "BackColor", "ForeColor") {
        $o | Add-Member -MemberType ScriptProperty -Name $p `
            -Value ([scriptblock]::Create("RadGet `$this.Path '$p'")) `
            -SecondValue ([scriptblock]::Create("param(`$v) RadSet `$this.Path '$p' `$v"))
    }
    foreach ($p in "Enabled", "Visible") {
        $o | Add-Member -MemberType ScriptProperty -Name $p `
            -Value ([scriptblock]::Create("RadToBool (RadGet `$this.Path '$p')")) `
            -SecondValue ([scriptblock]::Create("param(`$v) RadSet `$this.Path '$p' ([bool]`$v)"))
    }
    foreach ($p in "Left", "Top", "Width", "Height", "ListIndex", "Interval") {
        $o | Add-Member -MemberType ScriptProperty -Name $p `
            -Value ([scriptblock]::Create("[int](RadToNumber (RadGet `$this.Path '$p'))")) `
            -SecondValue ([scriptblock]::Create("param(`$v) RadSet `$this.Path '$p' `$v"))
    }
    $o | Add-Member -MemberType ScriptProperty -Name ListCount -Value { [int](RadToNumber (RadGet $this.Path 'ListCount')) }
    $o | Add-Member -MemberType ScriptMethod -Name Get -Value { param($p) RadGet $this.Path $p }
    $o | Add-Member -MemberType ScriptMethod -Name Set -Value { param($p, $v) RadSet $this.Path $p $v }
    $o | Add-Member -MemberType ScriptMethod -Name Call -Value { RadInvoke $this.Path @args }
    $o | Add-Member -MemberType ScriptMethod -Name AddItem -Value { param($item) [void](RadInvoke $this.Path 'AddItem' $item) }
    $o | Add-Member -MemberType ScriptMethod -Name RemoveItem -Value { param($i) [void](RadInvoke $this.Path 'RemoveItem' $i) }
    $o | Add-Member -MemberType ScriptMethod -Name Clear -Value { [void](RadInvoke $this.Path 'Clear') }
    $o | Add-Member -MemberType ScriptMethod -Name List -Value { param($i) RadInvoke $this.Path 'List' $i }
    $o | Add-Member -MemberType ScriptMethod -Name SetFocus -Value { [void](RadInvoke $this.Path 'SetFocus') }
    $o | Add-Member -MemberType ScriptMethod -Name Move -Value { param($l, $t, $w, $h) [void](RadInvoke $this.Path 'Move' $l $t $w $h) }
    $o | Add-Member -MemberType ScriptMethod -Name ShowDialog -Value { RadInvoke $this.Path 'ShowDialog' }
    $o | Add-Member -MemberType ScriptMethod -Name Show -Value { RadShow $this.Path }
    $o | Add-Member -MemberType ScriptMethod -Name Hide -Value { RadHide $this.Path }
    $o | Add-Member -MemberType ScriptMethod -Name ToString -Value { $this.Path } -Force
    return $o
}

# Event arguments: Sender, Name, Args, X, Y, Button, KeyCode, KeyChar
function New-RadEvent([string]$Sender, [string]$Name, [string]$Text) {
    $p = @(($Text -split ' ') | Where-Object { $_ -ne '' })
    $n = { param($i) if ($i -lt $p.Count) { [int](RadToNumber $p[$i]) } else { 0 } }
    return [pscustomobject]@{
        Sender = $Sender; Name = $Name; Args = $Text
        X = (& $n 0); Y = (& $n 1); Button = (& $n 2); KeyCode = (& $n 3)
        KeyChar = $(if ($p.Count -gt 4) { $p[4] } else { "" })
    }
}

# ---------------------------------------------------------------- RAD Hub (cross-language calls)
function radcall {
    param([Parameter(Mandatory = $true, Position = 0)][string]$Function,
          [Parameter(ValueFromRemainingArguments = $true)]$Arguments)
    if ($null -eq $script:RadHub) {
        $addr = $env:RAD_HUB
        if (-not $addr) { throw "RAD Hub is not running (RAD_HUB is not set)" }
        $i = $addr.LastIndexOf(':')
        $client = New-Object System.Net.Sockets.TcpClient($addr.Substring(0, $i), [int]$addr.Substring($i + 1))
        $client.NoDelay = $true
        $stream = $client.GetStream()
        $w = New-Object System.IO.StreamWriter($stream, $script:RadUtf8)
        $w.AutoFlush = $true
        $script:RadHub = @{ Client = $client; In = (New-Object System.IO.StreamReader($stream, $script:RadUtf8)); Out = $w; Id = 0 }
    }
    $hub = $script:RadHub
    $hub.Id++
    $list = New-Object System.Collections.ArrayList
    foreach ($a in @($Arguments)) { if ($null -ne $Arguments) { [void]$list.Add($a) } }
    $req = @{ id = $hub.Id; call = $Function; args = $list } | ConvertTo-Json -Compress -Depth 20
    $hub.Out.Write($req + "`n")
    while ($true) {
        $line = $hub.In.ReadLine()
        if ($null -eq $line) { $script:RadHub = $null; throw "RAD Hub closed the connection" }
        $r = $line | ConvertFrom-Json
        if ($null -ne $r.id -and $r.id -ne $hub.Id) { continue }
        if ($null -ne $r.error) { throw "${Function}: $($r.error)" }
        $res = $r.result
        if ($res -is [array]) { return , $res }
        return $res
    }
}
