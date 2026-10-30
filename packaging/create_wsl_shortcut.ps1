param(
    [string]$Distro = 'Ubuntu',
    [string]$ProjectDir = '/home/big-kola/FloodGuard-Studio'
)

$ErrorActionPreference = 'Stop'

$supportDir = Join-Path $env:LOCALAPPDATA 'FloodGuardStudio'
New-Item -ItemType Directory -Force -Path $supportDir | Out-Null

$launcher = Join-Path $supportDir 'launch_floodguard.vbs'
$icon = Join-Path $supportDir 'floodguard_studio.ico'

$bashCommand = "cd $ProjectDir && exec ./scripts/launch_floodguard.sh"
$vbsLine = 'shell.Run "wsl.exe -d ' + $Distro + ' -- bash -lc ""' + $bashCommand + '""", 0, False'
$vbs = 'Set shell = CreateObject("WScript.Shell")' + "`r`n" + $vbsLine
Set-Content -Path $launcher -Value $vbs -Encoding ASCII

if (-not (Test-Path $icon)) {
    Write-Warning "Icon not found at $icon; the shortcut will use the default icon."
}

$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'FloodGuard Studio.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)

$shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\wscript.exe'
$shortcut.Arguments = '"' + $launcher + '"'
$shortcut.WorkingDirectory = $env:USERPROFILE
if (Test-Path $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Description = 'Launch FloodGuard Studio'
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Output $shortcutPath
