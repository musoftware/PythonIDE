# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module Organizer - groups files by type and plans where they would go. It only READS the folder:
# nothing is moved, copied or deleted.

$script:TargetOf = @{
    Images    = ".jpg .jpeg .png .gif .bmp .webp .svg .ico"
    Documents = ".pdf .doc .docx .txt .rtf .odt .md .xls .xlsx .csv .ppt .pptx"
    Music     = ".mp3 .wav .ogg .flac .m4a"
    Videos    = ".mp4 .mkv .avi .mov .webm"
    Archives  = ".zip .7z .rar .tar .gz"
    Code      = ".py .js .ts .ps1 .rb .lua .pl .c .cpp .cs .java .html .css .json"
    Programs  = ".exe .msi .bat .cmd"
}

function Get-TargetFolder([string]$Extension) {
    foreach ($k in $script:TargetOf.Keys) {
        if ((" " + $script:TargetOf[$k] + " ").Contains(" " + $Extension.ToLower() + " ")) { return $k }
    }
    return "Other"
}

# One object per extension: Extension, Files, KB, Target (sorted by number of files)
function Get-TypeSummary([string]$Folder, [bool]$Recurse) {
    $files = Get-ChildItem -LiteralPath $Folder -File -Recurse:$Recurse -ErrorAction SilentlyContinue
    $files | Group-Object { if ($_.Extension) { $_.Extension.ToLower() } else { "(none)" } } | ForEach-Object {
        [pscustomobject]@{
            Extension = $_.Name
            Files     = $_.Count
            KB        = [Math]::Round((($_.Group | Measure-Object Length -Sum).Sum) / 1KB, 1)
            Target    = Get-TargetFolder $_.Name
        }
    } | Sort-Object Files -Descending
}

# "name -> Target\" lines (what an organizer would do)
function Get-MovePlan([string]$Folder, [bool]$Recurse) {
    Get-ChildItem -LiteralPath $Folder -File -Recurse:$Recurse -ErrorAction SilentlyContinue |
        Sort-Object Name | ForEach-Object { "{0} -> {1}\" -f $_.Name, (Get-TargetFolder $_.Extension) }
}
