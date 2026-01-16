#!/bin/bash

set -e

echo "=== Setting up Tailscale Serve for Vesla Dashboard ==="
echo

# Set current user as Tailscale operator (one-time setup)
echo "Step 1: Setting $USER as Tailscale operator..."
sudo tailscale set --operator=$USER
echo "✓ Operator set"
echo

# Set up Tailscale serve to expose port 5002
echo "Step 2: Configuring Tailscale Serve for port 5002..."
tailscale serve --bg 5002
echo "✓ Tailscale Serve configured"
echo

# Show current serve status
echo "Step 3: Current Tailscale Serve status:"
tailscale serve status
echo

# Get Tailscale hostname
TAILSCALE_HOSTNAME=$(tailscale status --json | grep -oP '"HostName":\s*"\K[^"]+' | head -1)

echo "=== Setup Complete ==="
echo
echo "Dashboard is now accessible via Tailscale at:"
echo "  https://${TAILSCALE_HOSTNAME}"
echo
echo "This URL is ONLY accessible from devices on your Tailscale network."
echo "Public internet access is completely blocked."
echo
echo "To check status:"
echo "  tailscale serve status"
echo
echo "To stop serving:"
echo "  tailscale serve reset"
echo
