<#
Build script for Windows: runs PyInstaller and then (optionally) Inno Setup.
Requires: Python, pip, PyInstaller installed. If Inno Setup is installed and `ISCC.exe`
is on PATH, the script will attempt to compile `installer\app.iss`.
#>
param(
    [string]$IconPath = "assets\app.ico",
    [switch]$NoInno
)

Write-Output "Ensuring pip is up to date and installing PyInstaller..."
python -m pip install --upgrade pip
pip install pyinstaller

$pyInstallerCmd = "pyinstaller --onefile --windowed --name \"FileManager\" gui_entry.py"
if (Test-Path $IconPath) {
    $pyInstallerCmd = "$pyInstallerCmd --icon=$IconPath"
} else {
    Write-Output "Icon not found at $IconPath — building without icon."
}

Write-Output "Running: $pyInstallerCmd"
Invoke-Expression $pyInstallerCmd

if (-not $NoInno) {
    # Try to run Inno Setup compiler if available
    $iscc = "ISCC.exe"
    $found = Get-Command $iscc -ErrorAction SilentlyContinue
    if ($found) {
        Write-Output "Found ISCC — building installer from installer\app.iss"
        & $iscc "installer\app.iss"
    } else {
        Write-Output "ISCC not found in PATH — skipping Inno Setup compilation."
    }
}

Write-Output "Build finished. Check the 'dist' directory for FileManager.exe and 'installer' for output." 
