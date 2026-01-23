# AEGIS Local Development Environment Shutdown Script

$ErrorActionPreference = "Stop"

Write-Host "Stopping AEGIS local environment..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dockerDir = Join-Path (Split-Path -Parent $scriptDir) "docker"

Set-Location $dockerDir
docker-compose down

Write-Host "Environment stopped." -ForegroundColor Green
