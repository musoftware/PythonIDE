# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# System Info - event handlers for Form1 (PowerShell, GUI Bridge).
# Shows: CIM/WMI queries in a module (SysInfo.ps1), DataGridView, ListBoxes, ProgressBar, a Timer (clock +
#        auto refresh), SaveFileDialog (save a text report), menus with a check-style toggle, StatusBar.
# Everything is read-only: the program never changes the computer.

$script:AutoRefresh = $false
$script:Ticks = 0

function Show-Info {
    $grdInfo.Clear()
    foreach ($row in Get-SysRows) {
        [void](RadInvoke grdInfo AddItem $row[0] $row[1] $row[2])      # one argument per cell
    }
    Show-Usage
    $lstDrives.Clear()
    foreach ($line in Get-DriveLines) { $lstDrives.AddItem($line) }
    $sbStatus.Text = "Updated " + (Get-Date -Format "HH:mm:ss")
}

function Show-Usage {
    $prgMemory.Value = Get-MemoryPercent
    $lblMemText.Text = Get-MemoryText
    $lstProcesses.Clear()
    foreach ($line in Get-TopProcesses 10) { $lstProcesses.AddItem($line) }
}

function Form1_Load($e) {
    Show-Info
}

function cmdRefresh_Click($e) { Show-Info }
function mnuFileRefresh_Click($e) { Show-Info }

function tmrClock_Tick($e) {
    $lblClock.Text = Get-Date -Format "HH:mm:ss"
    $script:Ticks++
    if ($script:AutoRefresh -and ($script:Ticks % 5 -eq 0)) { Show-Usage }    # every 5 seconds
}

function mnuViewAuto_Click($e) {
    $script:AutoRefresh = -not $script:AutoRefresh
    RadSet mnuViewAuto Checked $script:AutoRefresh
    $sbStatus.Text = $(if ($script:AutoRefresh) { "Auto refresh: on (memory and processes every 5 s)" } else { "Auto refresh: off" })
}

function mnuFileSave_Click($e) {
    if ((RadInvoke dlgSave ShowSave) -ne "OK") { return }
    $file = RadGet dlgSave FileName
    $lines = @("System report - " + (Get-Date -Format "yyyy-MM-dd HH:mm"), "")
    foreach ($row in Get-SysRows) { $lines += ("{0,-10} {1,-16} {2}" -f $row[0], $row[1], $row[2]) }
    $lines += "", "Drives:"
    $lines += Get-DriveLines
    $lines += "", "Top processes:"
    $lines += Get-TopProcesses 10
    [IO.File]::WriteAllLines($file, [string[]]$lines, (New-Object System.Text.UTF8Encoding $false))
    MsgBox "Report saved to $file" | Out-Null
}

function mnuFileExit_Click($e) { RadEnd }
