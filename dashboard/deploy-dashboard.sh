#!/bin/bash

set -e

echo "=== Deploying Vesla Mission Control Dashboard ==="
echo

cd /opt/vesla/dashboard

# Build Docker image
echo "Building Docker image..."
docker build -t vesla-dashboard:latest .
echo "✓ Built Docker image"

# Stop and remove old container if exists
if docker ps -a --format '{{.Names}}' | grep -q '^vesla-dashboard$'; then
    echo
    echo "Removing old container..."
    docker rm -f vesla-dashboard || true
    echo "✓ Removed old container"
fi

# Deploy with docker-compose
echo
echo "Deploying with Docker Compose..."
docker compose up -d
echo "✓ Deployed container"

# Wait for container to be ready
echo
echo "Waiting for dashboard to be ready..."
sleep 3

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q '^vesla-dashboard$'; then
    echo "✓ Container is running"
else
    echo "✗ Container is not running"
    exit 1
fi

# Show container info
echo
echo "=== Deployment Complete ==="
echo
echo "Container status:"
docker ps | grep vesla-dashboard
echo
echo "Dashboard should be accessible at:"
echo "  - Local: http://localhost:5002"
echo "  - Via Tailscale: https://dashboard.vesla-app.site (Tailscale network only)"
echo
echo "Note: Dashboard is restricted to Tailscale network (100.64.0.0/10)"
echo "Access will be blocked from public internet for security."
echo
echo "View logs:"
echo "  docker logs -f vesla-dashboard"
echo
