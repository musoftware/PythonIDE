# RAD IDE - PowerShell Gallery helper used by Project > Packages.
#   radpkg.ps1 list | search <text> | install <Name[@Version]> | uninstall <Name>
# Modules are installed for the current user (no administrator rights needed) and are available
# to every PowerShell program (Import-Module <Name>, or just call its commands).
param([Parameter(Mandatory = $true)][string]$Action, [string]$Name = "")

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }

function Initialize-Gallery {
    # PowerShell 5.1 needs the NuGet provider for the gallery; install it silently for the current user.
    if (-not (Get-PackageProvider -ListAvailable -Name NuGet -ErrorAction SilentlyContinue |
              Where-Object { $_.Version -ge [version]"2.8.5.201" })) {
        Write-Output "Installing the NuGet package provider (one time) ..."
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force | Out-Null
    }
}

try {
    switch ($Action.ToLower()) {
        "list" {
            $mods = @(Get-InstalledModule -ErrorAction SilentlyContinue)
            if ($mods.Count -eq 0) { Write-Output "No modules installed from the PowerShell Gallery." }
            else { $mods | Sort-Object Name | Format-Table -AutoSize Name, Version, Repository | Out-String -Width 200 }
        }
        "search" {
            Initialize-Gallery
            $q = if ($Name) { "*$Name*" } else { "*" }
            $found = @(Find-Module -Name $q -Repository PSGallery -ErrorAction SilentlyContinue | Select-Object -First 30)
            if ($found.Count -eq 0) { Write-Output "No modules found." }
            else { $found | Format-Table -AutoSize Name, Version, Description | Out-String -Width 220 }
        }
        { $_ -in "install", "add" } {
            if (-not $Name) { throw "no module name given" }
            Initialize-Gallery
            $n, $v = $Name -split '[@:]', 2
            $p = @{ Name = $n; Scope = "CurrentUser"; Force = $true; AllowClobber = $true; Repository = "PSGallery" }
            if ($v) { $p.RequiredVersion = $v }
            Install-Module @p
            $m = Get-InstalledModule -Name $n
            Write-Output "Installed $($m.Name) $($m.Version) (current user)."
        }
        { $_ -in "uninstall", "remove" } {
            if (-not $Name) { throw "no module name given" }
            Uninstall-Module -Name $Name -AllVersions -Force
            Write-Output "Removed $Name."
        }
        default { throw "unknown action '$Action' (list, search, install, uninstall)" }
    }
}
catch {
    [Console]::Error.WriteLine("PowerShell Gallery: $($_.Exception.Message)")
    exit 1
}
