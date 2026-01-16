#!/bin/bash
# Install Vesla CLI

set -e

echo "Installing Vesla CLI..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install --user -r requirements.txt

# Make CLI executable
chmod +x vesla

# Install CLI to user bin
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

cp vesla "$INSTALL_DIR/vesla"

echo ""
echo "✓ Vesla CLI installed successfully!"
echo ""
echo "Make sure $INSTALL_DIR is in your PATH."
echo "Add this to your ~/.bashrc or ~/.zshrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "Configure the CLI:"
echo "  vesla config set server_url https://api.vesla-app.site"
echo "  vesla config set api_token YOUR_API_TOKEN"
echo ""
echo "Usage:"
echo "  vesla init    # Initialize project"
echo "  vesla push    # Deploy to server"
echo "  vesla status <app>   # Check app status"
echo "  vesla logs <app>     # View logs"
echo "  vesla delete <app>   # Delete app"
