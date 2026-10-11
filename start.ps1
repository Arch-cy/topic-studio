param([int]$Port = 8501, [string]$Python = "")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$localPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$workspacePython = Join-Path $PSScriptRoot "..\..\work\topic-lab-venv\Scripts\python.exe"
if (-not $Python) {
    if (Test-Path -LiteralPath $localPython) { $Python = $localPython }
    elseif (Test-Path -LiteralPath $workspacePython) { $Python = $workspacePython }
    else { throw "Python environment not found. Create .venv and install requirements.txt first, or pass -Python." }
}
while (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { $Port++ }
Write-Host "Topic Studio: http://127.0.0.1:$Port"
& $Python -m streamlit run app.py --server.address 127.0.0.1 --server.port $Port --server.headless true
