# Yazaki Chatbot Frontend - Quick Start Script
# This script starts a simple HTTP server to serve the frontend

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Yazaki Chatbot Frontend Server" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
}

if ($pythonCmd) {
    Write-Host "✓ Python detected" -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting frontend server..." -ForegroundColor Yellow
    Write-Host "Frontend URL: " -NoNewline
    Write-Host "http://localhost:8000" -ForegroundColor Green
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
    Write-Host ""
    
    # Start Python HTTP server
    & $pythonCmd -m http.server 8000
    
} else {
    Write-Host "⚠ Python not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Opening index.html directly in browser..." -ForegroundColor Yellow
    Write-Host ""
    
    # Open directly in default browser
    $indexPath = Join-Path $PSScriptRoot "index.html"
    Start-Process $indexPath
    
    Write-Host "✓ Opened in browser" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: For better compatibility, install Python and run this script again." -ForegroundColor Gray
}
