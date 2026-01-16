#!/bin/bash
# Install Vesla Server systemd service

set -e

echo "Installing Vesla Server systemd service..."

# Check if venv exists
if [ ! -d "/opt/vesla/server/venv" ]; then
    echo "Error: Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Copy service file to systemd directory
sudo cp vesla-server.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable vesla-server

echo ""
echo "✓ Vesla Server service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start vesla-server"
echo "  Stop:    sudo systemctl stop vesla-server"
echo "  Status:  sudo systemctl status vesla-server"
echo "  Logs:    sudo journalctl -u vesla-server -f"
echo ""
echo "The API will be available at: http://127.0.0.1:5001"
echo "Configure Traefik to route to this endpoint for HTTPS access."
