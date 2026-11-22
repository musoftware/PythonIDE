# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# File Organizer (preview) - event handlers for Form1 (PowerShell, GUI Bridge).
# Shows: FolderBrowserDialog, Get-ChildItem / Group-Object in a module (Organizer.ps1), DataGridView, ListBox,
#        CheckBox, KeyPress (Enter scans), exporting the plan to CSV, menus, MsgBox. It never moves files.

function Form1_Load($e) {
    $txtFolder.Text = [Environment]::GetFolderPath("MyDocuments")
    $sbStatus.Text = "Choose a folder and press Scan - files are only listed, never moved"
}

function cmdBrowse_Click($e) {
    RadSet dlgFolder SelectedPath $txtFolder.Text
    if ((RadInvoke dlgFolder ShowFolder) -eq "OK") {
        $txtFolder.Text = RadGet dlgFolder SelectedPath
        cmdScan_Click $e
    }
}

function mnuFileBrowse_Click($e) { cmdBrowse_Click $e }

function cmdScan_Click($e) {
    $folder = $txtFolder.Text.Trim()
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
        MsgBox "The folder '$folder' does not exist." | Out-Null
        return
    }
    $recurse = (RadGet chkRecurse Value) -eq "1"
    $grdTypes.Clear()
    $total = 0
    foreach ($t in Get-TypeSummary $folder $recurse) {
        [void](RadInvoke grdTypes AddItem $t.Extension $t.Files $t.KB $t.Target)
        $total += $t.Files
    }
    $lstPlan.Clear()
    $script:Plan = @(Get-MovePlan $folder $recurse)
    foreach ($line in $script:Plan | Select-Object -First 500) { $lstPlan.AddItem($line) }
    $sbStatus.Text = "$total file(s) in $folder" + $(if ($script:Plan.Count -gt 500) { " (first 500 shown)" } else { "" })
}

function txtFolder_KeyPress($e) {
    if ($e.Args -match "Return") { cmdScan_Click $e }
}

function mnuFileExport_Click($e) {
    if (-not $script:Plan) { MsgBox "Scan a folder first." | Out-Null; return }
    $out = Join-Path $RadProject "plan.csv"
    $script:Plan | ForEach-Object {
        $name, $target = $_ -split " -> "
        [pscustomobject]@{ File = $name; Target = $target.TrimEnd("\") }
    } | Export-Csv -LiteralPath $out -NoTypeInformation -Encoding UTF8
    MsgBox "Plan exported to $out ($($script:Plan.Count) rows)" | Out-Null
}

function mnuFileExit_Click($e) { RadEnd }
