#!/bin/bash
# fckgit MCP Server Installation Script for iPad/Linux
# Located in: scripts/install_mcp.sh
# Run this after installing fckgit to add MCP support

echo "========================================"
echo "fckgit MCP Server Installation"
echo "========================================"
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found! Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"

# Install MCP
echo ""
echo "Installing MCP Python SDK and dependencies..."
pip3 install "mcp>=1.0.0" "psutil>=5.9.0"

if [ $? -ne 0 ]; then
    echo "Failed to install MCP dependencies"
    exit 1
fi

echo "MCP dependencies installed successfully!"

# Test the setup
echo ""
echo "Testing MCP server setup..."
python3 test_mcp.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Warning: Test encountered issues"
    echo "This might be because you're not in a git repository"
else
    echo ""
    echo "MCP server test completed!"
fi

# Show next steps
echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Get your Gemini API key from: https://makersuite.google.com/app/apikey"
echo "2. Read MCP_SETUP.md for configuration instructions"
echo "3. Configure your AI assistant (Cursor/Claude Desktop)"
echo "4. Restart your AI assistant"
echo ""
echo "Example config locations:"
echo "  Mac (Claude): ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Linux (Claude): ~/.config/Claude/claude_desktop_config.json"
echo ""
echo "See mcp_config_example.json for configuration template"
