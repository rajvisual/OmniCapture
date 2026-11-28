<#
.SYNOPSIS
Creates a 1-click Windows Desktop Shortcut for OmniCapture Studio.
#>

$repoRoot = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "OmniCapture Studio.lnk"
$iconPath = Join-Path $repoRoot "assets\logo\omnicapture.ico"
$exePath = Join-Path $repoRoot "dist\OmniCapture\OmniCapture.exe"
$vbsPath = Join-Path $repoRoot "OmniCapture Studio.vbs"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)

if (Test-Path $exePath) {
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = Split-Path -Parent $exePath
    $shortcut.Description = "OmniCapture Studio — Native Windows 11 Desktop Application"
} else {
    $shortcut.TargetPath = "wscript.exe"
    $shortcut.Arguments = "`"$vbsPath`""
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.Description = "OmniCapture Studio (Source Launcher)"
}

if (Test-Path $iconPath) {
    $shortcut.IconLocation = "$iconPath,0"
}

$shortcut.Save()
Write-Host "[✓] Desktop shortcut created: $shortcutPath" -ForegroundColor Green
