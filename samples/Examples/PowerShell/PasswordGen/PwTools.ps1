# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module PwTools - password generation with a cryptographic random generator, and a strength estimate.

$script:Sets = @{
    Upper   = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    Lower   = "abcdefghijkmnopqrstuvwxyz"
    Digits  = "23456789"
    Symbols = "!@#$%^&*-_=+?"
}

function Get-RandomIndex([int]$Max) {
    # unbiased random number 0..Max-1 from RNGCryptoServiceProvider (works in Windows PowerShell 5.1 and 7)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 4
    $limit = [uint32]::MaxValue - ([uint32]::MaxValue % [uint32]$Max)
    do { $rng.GetBytes($bytes); $n = [BitConverter]::ToUInt32($bytes, 0) } while ($n -ge $limit)
    $rng.Dispose()
    return [int]($n % [uint32]$Max)
}

# One character of every chosen set is guaranteed; the rest is random from all of them; then shuffled.
function New-Password([int]$Length, [bool]$Upper, [bool]$Lower, [bool]$Digits, [bool]$Symbols) {
    $chosen = @()
    if ($Upper) { $chosen += $script:Sets.Upper }
    if ($Lower) { $chosen += $script:Sets.Lower }
    if ($Digits) { $chosen += $script:Sets.Digits }
    if ($Symbols) { $chosen += $script:Sets.Symbols }
    if ($chosen.Count -eq 0) { throw "Choose at least one kind of character." }
    $all = -join $chosen
    $chars = New-Object System.Collections.ArrayList
    foreach ($set in $chosen) { [void]$chars.Add($set[(Get-RandomIndex $set.Length)]) }
    while ($chars.Count -lt $Length) { [void]$chars.Add($all[(Get-RandomIndex $all.Length)]) }
    for ($i = $chars.Count - 1; $i -gt 0; $i--) {          # Fisher-Yates shuffle
        $j = Get-RandomIndex ($i + 1)
        $tmp = $chars[$i]; $chars[$i] = $chars[$j]; $chars[$j] = $tmp
    }
    return -join $chars
}

# Entropy in bits = length * log2(size of the alphabet used); 0..100 score and a label (English + Arabic)
function Get-Strength([string]$Text) {
    $pool = 0
    if ($Text -cmatch "[A-Z]") { $pool += 26 }
    if ($Text -cmatch "[a-z]") { $pool += 26 }
    if ($Text -match "[0-9]") { $pool += 10 }
    if ($Text -match "[^A-Za-z0-9]") { $pool += 15 }
    $bits = if ($pool -gt 0) { [Math]::Round($Text.Length * [Math]::Log($pool, 2)) } else { 0 }
    $score = [Math]::Min(100, [int]($bits))
    if ($bits -lt 40) { $label = "Weak"; $ar = "ضعيفة" }
    elseif ($bits -lt 70) { $label = "Fair"; $ar = "متوسطة" }
    elseif ($bits -lt 100) { $label = "Strong"; $ar = "قوية" }
    else { $label = "Very strong"; $ar = "قوية جدا" }
    return [pscustomobject]@{ Bits = $bits; Score = $score; Label = $label; Arabic = $ar }
}
