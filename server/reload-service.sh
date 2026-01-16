#!/bin/bash
# Reload and restart vesla-server service

set -e

echo "Reloading vesla-server service..."

# Copy updated service file
sudo cp vesla-server.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart vesla-server

# Show status
echo ""
sudo systemctl status vesla-server --no-pager -l

echo ""
echo "✓ Service reloaded and restarted"
