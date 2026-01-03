# fckgit MCP Server Installation Script for Windows
# Located in: scripts/install_mcp.ps1
# Run this after installing fckgit to add MCP support

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "fckgit MCP Server Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Install MCP
Write-Host ""
Write-Host "Installing MCP Python SDK and dependencies..." -ForegroundColor Yellow
pip install "mcp>=1.0.0" "psutil>=5.9.0"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install MCP dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "MCP dependencies installed successfully!" -ForegroundColor Green

# Test the setup
Write-Host ""
Write-Host "Testing MCP server setup..." -ForegroundColor Yellow
python test_mcp.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Warning: Test encountered issues" -ForegroundColor Yellow
    Write-Host "This might be because you're not in a git repository" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "MCP server test completed!" -ForegroundColor Green
}

# Show next steps
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Get your Gemini API key from: https://makersuite.google.com/app/apikey" -ForegroundColor White
Write-Host "2. Read MCP_SETUP.md for configuration instructions" -ForegroundColor White
Write-Host "3. Configure your AI assistant (Cursor/Claude Desktop)" -ForegroundColor White
Write-Host "4. Restart your AI assistant" -ForegroundColor White
Write-Host ""
Write-Host "Example Cursor config location:" -ForegroundColor Yellow
Write-Host "  Windows: %APPDATA%\Cursor\User\globalStorage\config.json" -ForegroundColor White
Write-Host ""
Write-Host "See mcp_config_example.json for configuration template" -ForegroundColor Yellow
