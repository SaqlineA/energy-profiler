$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& ./.venv/Scripts/python.exe -c "import fastapi, uvicorn, sklearn, httpx, matplotlib"
if ($LASTEXITCODE -ne 0) {
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
Write-Host 'Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.'
& ./.venv/Scripts/python.exe app.py
