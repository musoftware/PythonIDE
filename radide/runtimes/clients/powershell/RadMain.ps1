# RAD IDE - entry program for PowerShell projects (GENERATED into _build/<lang> when the program runs - do not edit).
#   RadMain.ps1                    GUI Bridge program: runs the function <Object>_<Event> for each EVENT
#   RadMain.ps1 -Worker <Module>   serves the functions of <Module>.ps1 to the RAD Hub (JSON lines)
param([string]$Worker = "")

$RadProject = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$RadFiles = @(<#FILES#>)
. (Join-Path $PSScriptRoot "Rad.ps1")

if ($Worker) {
    # stdout carries JSON only: user output goes to stderr
    function global:Write-Host { [Console]::Error.WriteLine(($args | ForEach-Object { "$_" }) -join " ") }
    # the module itself + the reference proxies (<Lib>.ref.ps1) it may use
    $__radRefs = @($RadFiles | Where-Object { $_ -like '*.ref.ps1' })
    $RadFiles = @($RadFiles | Where-Object { [IO.Path]::GetFileNameWithoutExtension($_) -eq $Worker })
    if ($RadFiles.Count -eq 0 -and (Test-Path -LiteralPath (Join-Path $RadProject "$Worker.ps1"))) { $RadFiles = @("$Worker.ps1") }
    if ($RadFiles.Count -eq 0) { [Console]::Error.WriteLine("[powershell worker] module '$Worker' was not found") }
    $RadFiles = @($__radRefs) + @($RadFiles)
}

# The files are UTF-8 (Windows PowerShell 5.1 would read BOM-less files as ANSI): parse them ourselves.
# Syntax errors are reported as file(line,col): error: message and stop the program.
$__radBad = $false
$__radBlocks = @()
foreach ($__radFile in $RadFiles) {
    $__radPath = Join-Path $RadProject $__radFile
    if (-not (Test-Path -LiteralPath $__radPath)) { continue }
    $__radTokens = $null; $__radErrors = $null
    $__radText = [System.IO.File]::ReadAllText($__radPath, [System.Text.Encoding]::UTF8)
    $__radAst = [System.Management.Automation.Language.Parser]::ParseInput($__radText, $__radPath,
        [ref]$__radTokens, [ref]$__radErrors)
    foreach ($__radErr in $__radErrors) {
        [Console]::Error.WriteLine("${__radFile}($($__radErr.Extent.StartLineNumber),$($__radErr.Extent.StartColumnNumber)): " +
            "error: $($__radErr.Message)")
        $__radBad = $true
    }
    $__radBlocks += , @($__radFile, $__radAst)
}
if ($__radBad) { exit 1 }
foreach ($__radBlock in $__radBlocks) {
    try { . $__radBlock[1].GetScriptBlock() }
    catch { [Console]::Error.WriteLine("$($__radBlock[0]): $($_.Exception.Message) $($_.InvocationInfo.PositionMessage)") }
}
# console mode: a project without forms is a script - its modules ran above, nothing waits for events
if (-not $Worker -and -not ($RadFiles | Where-Object { $_ -like '*_designer.ps1' })) { exit 0 }

function RadWriteOutput($Items) {
    foreach ($o in @($Items)) {
        if ($null -eq $o) { continue }
        $text = ($o | Out-String -Width 200).TrimEnd()
        foreach ($l in ($text -split "`r?`n")) { RadSend $l }
    }
}

if ($Worker) {
    # {"id":7,"func":"add","args":[2,3]} -> {"id":7,"result":5}
    while ($null -ne ($__radLine = RadReadLine)) {
        if (-not $__radLine.Trim()) { continue }
        $__radId = $null
        try {
            $__radReq = $__radLine | ConvertFrom-Json
            $__radId = $__radReq.id
            $__radFn = Get-Command -Name $__radReq.func -CommandType Function -ErrorAction SilentlyContinue
            if ($null -eq $__radFn) { throw "module $Worker has no function '$($__radReq.func)'" }
            $__radArgs = @()
            if ($null -ne $__radReq.args) { $__radArgs = @($__radReq.args) }
            $__radResult = & $__radFn @__radArgs
            $__radReply = [ordered]@{ id = $__radId; result = $__radResult }
        }
        catch {
            $__radReply = [ordered]@{ id = $__radId; error = "$($_.Exception.Message)" }
        }
        try { $__radJson = $__radReply | ConvertTo-Json -Compress -Depth 20 }
        catch {
            $__radJson = [ordered]@{ id = $__radId; error = "result is not JSON: $($_.Exception.Message)" } |
                ConvertTo-Json -Compress
        }
        RadSend ($__radJson -replace "`r?`n", "")
    }
    exit 0
}

# read inline (not through RadReadLine): a debugger that attaches (PSES, radide/debug_more.py) breaks at
# the next statement, and a break on a function's return loses its value - the event line would be lost
while ($null -ne ($__radLine = $script:RadIn.ReadLine())) {
    if ($__radLine -eq "QUIT") { break }
    if (-not $__radLine.StartsWith("EVENT ")) { continue }
    $__radParts = @($__radLine.Substring(6) -split ' ', 3)
    $__radObj = $__radParts[0]
    $__radEv = if ($__radParts.Count -gt 1) { $__radParts[1] } else { "" }
    $__radName = "${__radObj}_${__radEv}"
    try {
        $__radFn = Get-Command -Name $__radName -CommandType Function -ErrorAction SilentlyContinue
        if ($null -ne $__radFn) {
            $__radE = New-RadEvent $__radObj $__radEv $(if ($__radParts.Count -gt 2) { $__radParts[2] } else { "" })
            RadWriteOutput (& $__radFn $__radE)
        }
    }
    catch {
        [Console]::Error.WriteLine("Error in ${__radName}: $($_.Exception.Message)")
        [Console]::Error.WriteLine($_.InvocationInfo.PositionMessage)
    }
    finally {
        RadSend "DONE"
    }
}
exit 0
