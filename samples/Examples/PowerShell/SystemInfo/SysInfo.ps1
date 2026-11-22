# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module SysInfo - read-only facts about this PC (CIM/WMI, .NET and environment variables).
# Loaded before the forms, so Form1.ps1 calls these functions directly; other languages of a solution
# can call them through the RAD Hub: radcall("SysInfo.Get-MemoryPercent").

function Get-SysRows {
    # rows of (group, property, value) for the grid
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $boot = $os.LastBootUpTime
    $up = (Get-Date) - $boot
    return @(
        , @("System", "Computer name", $env:COMPUTERNAME)
        , @("System", "User", $env:USERNAME)
        , @("System", "Windows", "$($os.Caption) ($($os.Version))")
        , @("System", "Architecture", $os.OSArchitecture)
        , @("System", "Up time", ("{0} d {1} h {2} min" -f $up.Days, $up.Hours, $up.Minutes))
        , @("Hardware", "Manufacturer", $cs.Manufacturer)
        , @("Hardware", "Model", $cs.Model)
        , @("Hardware", "Processor", $cpu.Name.Trim())
        , @("Hardware", "Logical CPUs", "$($cs.NumberOfLogicalProcessors) CPUs")
        , @("Hardware", "Memory", ("{0:N1} GB" -f ($cs.TotalPhysicalMemory / 1GB)))
        , @("Runtime", "PowerShell", "$($PSVersionTable.PSVersion)")
        , @(".NET", "CLR", "$([Environment]::Version)")
        , @("Runtime", "Culture", (Get-Culture).Name)
    )
}

function Get-MemoryPercent {
    $os = Get-CimInstance Win32_OperatingSystem
    $used = $os.TotalVisibleMemorySize - $os.FreePhysicalMemory
    return [int](100 * $used / $os.TotalVisibleMemorySize)
}

function Get-MemoryText {
    $os = Get-CimInstance Win32_OperatingSystem
    $used = ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB
    return ("{0:N1} of {1:N1} GB" -f $used, ($os.TotalVisibleMemorySize / 1MB))
}

function Get-TopProcesses([int]$Count = 10) {
    Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First $Count | ForEach-Object {
        "{0,-22} {1,8:N0} MB" -f ($_.ProcessName.Substring(0, [Math]::Min(22, $_.ProcessName.Length))),
            ($_.WorkingSet64 / 1MB)
    }
}

function Get-DriveLines {
    Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
        $free = $_.FreeSpace / 1GB
        $size = $_.Size / 1GB
        "{0}  {1,7:N1} GB free of {2,7:N1} GB ({3}% used)" -f $_.DeviceID, $free, $size, [int](100 - 100 * $free / [Math]::Max($size, 0.001))
    }
}
