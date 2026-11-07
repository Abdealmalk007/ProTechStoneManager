$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if ($env:PYTHON_EXECUTABLE -and (Test-Path $env:PYTHON_EXECUTABLE)) {
    $python=$env:PYTHON_EXECUTABLE
} else {
    $command=Get-Command python.exe -ErrorAction SilentlyContinue
    if (!$command) { throw 'Python 3.13 is required; see README_AR.md' }
    $python=$command.Source
}
$arguments=@(
    '-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir',
    '--name','ProTechStoneManager',
    '--distpath',"$PSScriptRoot\Releases",
    '--workpath',"$PSScriptRoot\Build",
    '--specpath',"$PSScriptRoot\Build",
    '--hidden-import','PySide6.QtPdf',
    '--hidden-import','PySide6.QtPdfWidgets',
    '--hidden-import','xlsxwriter',
    '--hidden-import','report_center',
    '--hidden-import','inventory_storage',
    '--hidden-import','inventory_ui',
    '--hidden-import','dashboard_plus',
    '--hidden-import','company_settings',
    '--hidden-import','premium_reports',
    '--hidden-import','target_reports',
    '--hidden-import','attachment_viewer',
    '--hidden-import','live_metrics',
    '--hidden-import','client_materials',
    '--hidden-import','export_layout',
    '--add-data',"$PSScriptRoot\src\Assets;Assets",
    '--icon',"$PSScriptRoot\src\Assets\PorcelainManager.ico",
    "$PSScriptRoot\src\app.py"
)
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }
Write-Output ('PUBLIC_EXE='+ (Join-Path $PSScriptRoot 'Releases\ProTechStoneManager\ProTechStoneManager.exe'))
