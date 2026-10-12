<#
.SYNOPSIS
  One-click start for Home Information: brings up Redis + HI in the
  background if they aren't already running, then opens HI in an app window.

.DESCRIPTION
  If HI already answers on /health this only opens the window. Otherwise it
  uses the Redis on -RedisPort if one answers PING, or starts the in-memory
  fakeredis stand-in; then starts HI with the env from scripts/hi.env (the
  same defaults scripts/hi-dev.sh uses), waits for /health and opens the
  window. Both services run hidden under pythonw.exe; their logs and PID files
  are in <data>/logs. -Stop shuts them down again.

  The desktop/Start Menu shortcuts come from scripts/install-shortcuts.ps1.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\home-launcher.ps1
  powershell -ExecutionPolicy Bypass -File scripts\home-launcher.ps1 -Path /edit/start
  powershell -ExecutionPolicy Bypass -File scripts\home-launcher.ps1 -Stop
#>
[CmdletBinding()]
param(
    # Page to open. /edit/start opens the house in EDIT mode, ready to add items.
    [string]$Path = '/',
    [switch]$Stop,
    # Start the services but don't open a window.
    [switch]$NoWindow,
    [int]$Port = 8411,
    [int]$RedisPort = 0,
    # HI data (database, media, logs). Default: $env:HI_DATA_DIR or <repo>\.data\hi
    [string]$DataDir,
    # Python venv with HI's requirements. Default: $env:HI_VENV or apps\home-information\venv
    [string]$Venv
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (-not $DataDir) { $DataDir = if ($env:HI_DATA_DIR) { $env:HI_DATA_DIR } else { Join-Path $Root '.data\hi' } }
if (-not $Venv) { $Venv = if ($env:HI_VENV) { $env:HI_VENV } else { Join-Path $Root 'apps\home-information\venv' } }
$DataDir = [IO.Path]::GetFullPath($DataDir)
$LogDir = Join-Path $DataDir 'logs'
$Services = Join-Path $PSScriptRoot 'home_services.py'
$PythonW = Join-Path $Venv 'Scripts\pythonw.exe'
$BaseUrl = "http://127.0.0.1:$Port"
New-Item -ItemType Directory -Force $LogDir | Out-Null

function Write-Log([string]$Message) {
    $line = '{0:yyyy-MM-dd HH:mm:ss} {1}' -f (Get-Date), $Message
    Write-Verbose $line
    try { Add-Content -Path (Join-Path $LogDir 'launcher.log') -Value $line -Encoding utf8 } catch { }
}

# A small "Starting Home..." window while the services come up (~10 s).
$Splash = $null
function Show-Splash {
    if ($NoWindow) { return }
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Home'
    $form.ClientSize = New-Object System.Drawing.Size(320, 90)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.TopMost = $true
    $icon = Join-Path $PSScriptRoot 'home.ico'
    if (Test-Path $icon) { $form.Icon = New-Object System.Drawing.Icon($icon) }
    $label = New-Object System.Windows.Forms.Label
    $label.Text = 'Starting Home...'
    $label.Font = New-Object System.Drawing.Font('Segoe UI', 11)
    $label.SetBounds(20, 16, 280, 26)
    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Style = 'Marquee'
    $bar.SetBounds(20, 50, 280, 18)
    $form.Controls.AddRange(@($label, $bar))
    $form.Show()
    [System.Windows.Forms.Application]::DoEvents()
    $script:Splash = $form
}

function Close-Splash {
    if ($script:Splash) { $script:Splash.Close(); $script:Splash = $null }
}

function Show-Error([string]$Message) {
    Write-Log "ERROR: $Message"
    Close-Splash
    if ($NoWindow) { Write-Error $Message -ErrorAction Continue; exit 1 }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("$Message`n`nLogs: $LogDir", 'Home',
        'OK', 'Error') | Out-Null
    exit 1
}

# --- environment (scripts/hi.env; variables already set win) ---------------

$env:HI_DATA_DIR = $DataDir
foreach ($line in Get-Content (Join-Path $PSScriptRoot 'hi.env')) {
    if ($line -match '^\s*(#|$)') { continue }
    $key, $value = $line.Split('=', 2)
    if ([Environment]::GetEnvironmentVariable($key)) { continue }
    $value = $value.Trim().Replace('@ROOT@', $Root).Replace('@DATA@', $DataDir)
    [Environment]::SetEnvironmentVariable($key, $value)
}
if ($RedisPort) { $env:HI_REDIS_PORT = "$RedisPort" } else { $RedisPort = [int]$env:HI_REDIS_PORT }

# --- probes ------------------------------------------------------------------

function Test-Health {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "$BaseUrl/health" -Verbose:$false
        return $r.StatusCode -eq 200
    } catch { return $false }
}

# 'pong' if a Redis answers on the port, 'open' if something else does, else $null.
function Test-Redis([int]$P) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        if (-not $client.ConnectAsync('127.0.0.1', $P).Wait(500)) { return $null }
        $stream = $client.GetStream()
        $stream.ReadTimeout = 1000
        $ping = [Text.Encoding]::ASCII.GetBytes("*1`r`n`$4`r`nPING`r`n")
        $stream.Write($ping, 0, $ping.Length)
        $buf = New-Object byte[] 64
        $n = $stream.Read($buf, 0, $buf.Length)
        if ([Text.Encoding]::ASCII.GetString($buf, 0, $n) -like '+PONG*') { return 'pong' }
        return 'open'
    } catch {
        if ($client.Connected) { return 'open' }
        return $null
    } finally { $client.Close() }
}

function Test-PortOpen([int]$P) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { return $client.ConnectAsync('127.0.0.1', $P).Wait(500) } catch { return $false } finally { $client.Close() }
}

function Wait-Until([scriptblock]$Condition, [int]$Seconds, [scriptblock]$Abort = { $false }) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        if (& $Abort) { return $false }
        for ($i = 0; $i -lt 5; $i++) {
            if ($script:Splash) { [System.Windows.Forms.Application]::DoEvents() }
            Start-Sleep -Milliseconds 100
        }
    }
    return $false
}

# --- processes ---------------------------------------------------------------

function Get-Proc([int]$Id) { Get-CimInstance Win32_Process -Filter "ProcessId=$Id" }

function Get-ServicePid([string]$Name) {
    $file = Join-Path $LogDir "$Name.pid"
    if (-not (Test-Path $file)) { return $null }
    $id = [int](Get-Content $file -Raw)
    $proc = Get-Proc $id
    if ($proc -and $proc.CommandLine -match 'home_services\.py') { return $id }
    Remove-Item $file -ErrorAction SilentlyContinue
    return $null
}

function Start-HomeService([string]$Name, [int]$P) {
    if (-not (Test-Path $PythonW)) {
        Show-Error "No Python venv at $Venv. Create it first (see README, 'Running it')."
    }
    Write-Log "starting $Name on port $P"
    $argList = @("`"$Services`"", $Name, $P, "`"$LogDir`"")
    return Start-Process -FilePath $PythonW -ArgumentList $argList -WorkingDirectory $Root -PassThru
}

function Get-ProcArgs($Proc) { ($Proc.CommandLine -replace '^\s*("[^"]*"|\S+)\s*', '').Trim() }

function Stop-Tree([int]$Id) {
    # Kill the process plus any python parents running the same thing (the
    # venv's python.exe is a launcher that runs the real interpreter as a child,
    # and Django's autoreloader is a parent of the serving process).
    $proc = Get-Proc $Id
    if (-not $proc) { return }
    $parent = Get-Proc $proc.ParentProcessId
    Write-Log "stopping pid $Id ($($proc.CommandLine.Trim()))"
    Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
    if ($parent -and $parent.Name -like 'python*' -and (Get-ProcArgs $parent) -eq (Get-ProcArgs $proc)) {
        Stop-Tree $parent.ProcessId
    }
}

function Stop-HomeService([string]$Name, [int]$P, [string]$Pattern) {
    $id = Get-ServicePid $Name
    if ($id) { Stop-Tree $id }
    Remove-Item (Join-Path $LogDir "$Name.pid") -ErrorAction SilentlyContinue
    # Also stop a server started some other way (e.g. scripts/hi-dev.sh), but
    # only if it is one of ours: never a real Redis.
    $owners = Get-NetTCPConnection -State Listen -LocalPort $P -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($owner in $owners) {
        $proc = Get-Proc $owner
        if ($proc -and $proc.CommandLine -match $Pattern) { Stop-Tree $owner }
    }
}

# --- main --------------------------------------------------------------------

if ($Stop) {
    Stop-HomeService 'hi' $Port 'home_services\.py"?\s+hi\b|manage\.py"?\s+runserver'
    Stop-HomeService 'redis' $RedisPort 'home_services\.py"?\s+redis\b|fakeredis'
    Write-Log 'stopped'
    exit 0
}

# Only one launcher at a time per port, so double-clicks don't start two servers.
$mutex = New-Object System.Threading.Mutex($false, "Local\HomeLauncher-$Port")
try { [void]$mutex.WaitOne(300000) } catch [System.Threading.AbandonedMutexException] { }
try {
    if (Test-Health) {
        Write-Log "HI already up on $BaseUrl"
    } else {
        if (Test-PortOpen $Port) {
            Show-Error "Something is on port $Port but it isn't answering $BaseUrl/health. Try the 'Stop Home' shortcut, then start again."
        }
        Show-Splash

        switch (Test-Redis $RedisPort) {
            'pong' { Write-Log "using the Redis already on port $RedisPort" }
            'open' { Show-Error "Port $RedisPort is in use by something that isn't Redis." }
            default {
                $redis = Start-HomeService 'redis' $RedisPort
                if (-not (Wait-Until { (Test-Redis $RedisPort) -eq 'pong' } 30 { $redis.HasExited })) {
                    Show-Error "The Redis stand-in didn't come up on port $RedisPort."
                }
            }
        }

        $hi = Start-HomeService 'hi' $Port
        if (-not (Wait-Until { Test-Health } 300 { $hi.HasExited })) {
            Show-Error "Home Information didn't start. See hi.log."
        }
        Write-Log "HI up on $BaseUrl"
    }
} finally {
    $mutex.ReleaseMutex()
}

if ($NoWindow) { exit 0 }

# Prefer an app-style window (no tabs or address bar) from Edge or Chrome.
$url = $BaseUrl + $Path
$browser = $null
foreach ($exe in 'msedge.exe', 'chrome.exe') {
    foreach ($hive in 'HKCU:', 'HKLM:') {
        $key = "$hive\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\$exe"
        $candidate = (Get-ItemProperty $key -ErrorAction SilentlyContinue).'(default)'
        if (-not $browser -and $candidate -and (Test-Path $candidate)) { $browser = $candidate }
    }
}
if ($browser) {
    Write-Log "opening $url in $browser"
    Start-Process -FilePath $browser -ArgumentList "--app=$url"
} else {
    Write-Log "opening $url in the default browser"
    Start-Process $url
}
# Keep the splash up until the window has had a moment to appear.
if ($Splash) { Wait-Until { $false } 2 | Out-Null }
Close-Splash
