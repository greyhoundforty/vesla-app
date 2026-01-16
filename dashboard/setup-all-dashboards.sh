#!/bin/bash

set -e

echo "=== Setting up Tailscale Serve for All Dashboards ==="
echo

# Set current user as Tailscale operator (one-time setup)
echo "Step 1: Setting $USER as Tailscale operator..."
sudo tailscale set --operator=$USER
echo "✓ Operator set"
echo

# Configure Tailscale serve for vesla dashboard (root path)
echo "Step 2: Configuring Tailscale Serve for Vesla Dashboard..."
tailscale serve --bg --set-path=/ http://127.0.0.1:5002
echo "✓ Vesla Dashboard configured at /"
echo

# Configure Tailscale serve for Traefik dashboard (traefik path)
echo "Step 3: Configuring Tailscale Serve for Traefik Dashboard..."
tailscale serve --bg --set-path=/traefik http://127.0.0.1:8080
echo "✓ Traefik Dashboard configured at /traefik"
echo

# Show current serve status
echo "Step 4: Current Tailscale Serve status:"
tailscale serve status
echo

# Get Tailscale hostname
TAILSCALE_HOSTNAME=$(tailscale status --json | grep -oP '"HostName":\s*"\K[^"]+' | head -1)

echo "=== Setup Complete ==="
echo
echo "Dashboards are now accessible via Tailscale at:"
echo "  Vesla Dashboard:   https://${TAILSCALE_HOSTNAME}/"
echo "  Traefik Dashboard: https://${TAILSCALE_HOSTNAME}/traefik"
echo
echo "These URLs are ONLY accessible from devices on your Tailscale network."
echo "Public internet access is completely blocked."
echo
echo "To check status:"
echo "  tailscale serve status"
echo
echo "To stop serving:"
echo "  tailscale serve reset"
echo
