# AEGIS Local Development Environment Startup Script
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AEGIS Local Development Environment  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Navigate to docker directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dockerDir = Join-Path (Split-Path -Parent $scriptDir) "docker"

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow

# Start containers
Set-Location $dockerDir
docker-compose up -d

Write-Host ""
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service health
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
Write-Host "---------------"

$services = @(
    @{Name="JanusGraph"; Port=8182; Url="http://localhost:8182"},
    @{Name="Kafka"; Port=9092; Url=$null},
    @{Name="Kafka UI"; Port=8080; Url="http://localhost:8080"},
    @{Name="PostgreSQL"; Port=5432; Url=$null},
    @{Name="Redis"; Port=6379; Url=$null},
    @{Name="MinIO Console"; Port=9001; Url="http://localhost:9001"}
)

foreach ($svc in $services) {
    $result = Test-NetConnection -ComputerName localhost -Port $svc.Port -WarningAction SilentlyContinue
    if ($result.TcpTestSucceeded) {
        $urlInfo = if ($svc.Url) { " -> $($svc.Url)" } else { "" }
        Write-Host "  [OK] $($svc.Name) (port $($svc.Port))$urlInfo" -ForegroundColor Green
    } else {
        Write-Host "  [--] $($svc.Name) (port $($svc.Port)) - starting..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Environment Ready!                   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Points:" -ForegroundColor White
Write-Host "  Kafka UI:      http://localhost:8080" -ForegroundColor Gray
Write-Host "  MinIO Console: http://localhost:9001 (aegis/aegis_dev_password)" -ForegroundColor Gray
Write-Host "  JanusGraph:    ws://localhost:8182/gremlin" -ForegroundColor Gray
Write-Host "  PostgreSQL:    localhost:5432 (aegis/aegis_dev_password)" -ForegroundColor Gray
Write-Host "  Redis:         localhost:6379" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop: docker-compose -f $dockerDir\docker-compose.yml down" -ForegroundColor Yellow
