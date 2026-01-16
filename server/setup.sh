#!/bin/bash
# Setup script for Vesla Server

set -e

echo "Setting up Vesla Server..."

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create virtual environment
echo "Creating virtual environment..."
cd /opt/vesla/server
python3 -m venv venv

# Activate and install Python dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✓ Vesla Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Review config.yaml and update settings as needed"
echo "2. Run: sudo ./install-service.sh to install systemd service"
echo "3. Start the service: sudo systemctl start vesla-server"
