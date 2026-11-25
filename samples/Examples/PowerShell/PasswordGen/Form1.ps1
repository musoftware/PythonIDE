# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Password Generator - event handlers for Form1 (PowerShell, GUI Bridge).
# Shows: NumericUpDown + CheckBoxes as options, a module with crypto-random functions (PwTools.ps1),
#        ProgressBar strength meter, an Arabic label, the clipboard (Set-Clipboard), history ListBox,
#        KeyPress on the form's controls (Enter = generate), menus, error handling with MsgBox.

function Show-Strength([string]$Text) {
    $s = Get-Strength $Text
    $prgStrength.Value = $s.Score
    $lblStrength.Text = "$($s.Label) ($($s.Bits) bits)"
    $lblStrengthAr.Text = "قوة كلمة المرور: $($s.Arabic)"
}

function cmdGenerate_Click($e) {
    $len = [int](RadToNumber (RadGet nudLength Value))
    $opts = foreach ($c in "chkUpper", "chkLower", "chkDigits", "chkSymbols") { (RadGet $c Value) -eq "1" }
    try {
        $pw = New-Password $len $opts[0] $opts[1] $opts[2] $opts[3]
    }
    catch {
        MsgBox $_.Exception.Message | Out-Null
        return
    }
    $txtPassword.Text = $pw
    Show-Strength $pw
    $lstHistory.AddItem((Get-Date -Format "HH:mm:ss") + "  " + $pw)
}

function Form1_Load($e) { cmdGenerate_Click $e }

# typing your own password shows its strength
function txtPassword_TextChanged($e) { Show-Strength $txtPassword.Text }

function nudLength_KeyPress($e) { if ($e.Args -match "^\S+ \S+ \S+ 13\b" -or $e.Args -match "Return") { cmdGenerate_Click $e } }

function cmdCopy_Click($e) {
    $pw = $txtPassword.Text
    if (-not $pw) { return }
    if ($env:RADEX_CLIPBOARD_FILE) {           # tests: write to a file instead of the user's clipboard
        [IO.File]::WriteAllText($env:RADEX_CLIPBOARD_FILE, $pw)
    }
    else {
        Set-Clipboard -Value $pw
    }
    RadSet Form1 Text "Password Generator - copied!"
}

function mnuEditCopy_Click($e) { cmdCopy_Click $e }
function mnuEditClear_Click($e) { $lstHistory.Clear() }

function mnuHelpAbout_Click($e) {
    MsgBox "Password Generator - a RAD IDE example in PowerShell $($PSVersionTable.PSVersion). Passwords come from a cryptographic random generator and are never saved." | Out-Null
}
