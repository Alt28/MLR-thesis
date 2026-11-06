$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 or later is required.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' main.py template
if ($LASTEXITCODE -ne 0) { throw 'Template creation failed.' }
if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    Push-Location -LiteralPath (Join-Path $PSScriptRoot 'frontend')
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed. Use Node.js 22.12 or later.' }
    } finally { Pop-Location }
} elseif (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw 'Install Node.js 22.12 or later, then run setup.ps1 again to build the frontend.'
} else {
    Write-Output 'Using the included compiled web interface. Node.js is needed only to rebuild it.'
}
Write-Output 'Setup complete. Double-click Start MLR System.bat.'
