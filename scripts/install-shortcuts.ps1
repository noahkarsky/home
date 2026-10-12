<#
.SYNOPSIS
  Adds "Home" shortcuts that run scripts\home-launcher.ps1 from this checkout.

.DESCRIPTION
  Desktop:     Home
  Start Menu:  Home\Home, Home\Home (Edit mode), Home\Stop Home

  Re-run it after moving the checkout. -DataDir and -Venv are passed through
  to the launcher, for data or a venv that isn't in the default place.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install-shortcuts.ps1
  powershell -ExecutionPolicy Bypass -File scripts\install-shortcuts.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$DataDir,
    [string]$Venv,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $PSScriptRoot 'home-launcher.ps1'
$Icon = Join-Path $PSScriptRoot 'home.ico'
$Desktop = [Environment]::GetFolderPath('Desktop')
$StartMenu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Home'

$passThrough = ''
if ($DataDir) { $passThrough += " -DataDir `"$([IO.Path]::GetFullPath($DataDir))`"" }
if ($Venv) { $passThrough += " -Venv `"$([IO.Path]::GetFullPath($Venv))`"" }

$shortcuts = @(
    @{ Dir = $Desktop;   Name = 'Home';             Args = '';                   Desc = 'Start Home Information and open it' }
    @{ Dir = $StartMenu; Name = 'Home';             Args = '';                   Desc = 'Start Home Information and open it' }
    @{ Dir = $StartMenu; Name = 'Home (Edit mode)'; Args = '-Path /edit/start';  Desc = 'Open Home Information in EDIT mode, to add items' }
    @{ Dir = $StartMenu; Name = 'Stop Home';        Args = '-Stop';              Desc = 'Stop the Home Information background services' }
)

if ($Uninstall) {
    foreach ($s in $shortcuts) { Remove-Item (Join-Path $s.Dir "$($s.Name).lnk") -ErrorAction SilentlyContinue }
    if ((Test-Path $StartMenu) -and -not (Get-ChildItem $StartMenu)) { Remove-Item $StartMenu }
    Write-Host 'Removed the Home shortcuts.'
    return
}

New-Item -ItemType Directory -Force $StartMenu | Out-Null
$powershell = Join-Path $PSHOME 'powershell.exe'
$shell = New-Object -ComObject WScript.Shell
foreach ($s in $shortcuts) {
    $path = Join-Path $s.Dir "$($s.Name).lnk"
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $powershell
    $lnk.Arguments = ("-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`" $($s.Args)".Trim() + $passThrough)
    $lnk.WorkingDirectory = $Root
    $lnk.IconLocation = "$Icon,0"
    $lnk.Description = $s.Desc
    $lnk.WindowStyle = 7  # minimized, so the console doesn't flash up
    $lnk.Save()
    Write-Host "Created $path"
}
