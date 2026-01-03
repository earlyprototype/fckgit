#!/bin/bash
# fckgit - One Click Install (It's Safe!)

set -e

echo "🏄‍♂️ fckgit installer - EXTREME MODE ACTIVATED"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first."
    exit 1
fi

echo "✓ Python found"

# Check Git
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Install it first."
    exit 1
fi

echo "✓ Git found"

# Install
echo ""
echo "📦 Installing fckgit..."
pip install . || python3 -m pip install .

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Get your free Gemini API key: https://makersuite.google.com/app/apikey"
echo "2. Create .env file: cp .env.example .env (then add your key)"
echo "3. Run: python3 -m fckgit"
echo ""
echo "🚀 Now go write some code. fckgit handles the rest."
