# RAD IDE - native build: loaded after the GUI Bridge client (Rad.ps1) inside the published exe.
# The client's I/O functions are redirected to the WinForms runtime of the exe (RadNative.PsBridge):
# the same SET/GET/CALL/MSGBOX/... lines, executed directly on the controls - no IDE, no Python.
function RadSend([string]$Line) { [void][RadNative.PsBridge]::Ask($Line) }
function RadAsk([string]$Line) { return [RadNative.PsBridge]::Ask($Line) }
function RadReadLine { return $null }
function RadEnd { [void][RadNative.PsBridge]::Ask("END") }

# radcall "Module.function" args... : every module of the project is loaded in this runspace
function radcall {
    param([Parameter(Mandatory = $true, Position = 0)][string]$Function,
          [Parameter(ValueFromRemainingArguments = $true)]$Arguments)
    $name = $Function.Substring($Function.LastIndexOf('.') + 1)
    $cmd = Get-Command -Name $name -CommandType Function -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { throw "${Function}: no such function in this program" }
    $list = @()
    if ($null -ne $Arguments) { $list = @($Arguments) }
    return & $cmd @list
}
