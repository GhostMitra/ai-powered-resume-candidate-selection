Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "    Launching AI Resume Screening & Candidate Matching Platform" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

python run_all.py
