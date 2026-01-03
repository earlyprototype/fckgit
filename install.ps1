# fckgit - One Click Install (It's Safe!)

Write-Host "🏄‍♂️ fckgit installer - EXTREME MODE ACTIVATED" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Install it first." -ForegroundColor Red
    exit 1
}

# Check Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git not found. Install it first." -ForegroundColor Red
    exit 1
}

# Install
Write-Host ""
Write-Host "📦 Installing fckgit..." -ForegroundColor Yellow
python -m pip install .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Get your free Gemini API key: https://makersuite.google.com/app/apikey"
    Write-Host "2. Create .env file: echo 'GEMINI_API_KEY=your_key_here' > .env"
    Write-Host "3. Run: python -m fckgit"
    Write-Host ""
    Write-Host "🚀 Now go write some code. fckgit handles the rest." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Installation failed. But you probably did not follow instructions anyway." -ForegroundColor Red
    exit 1
}
