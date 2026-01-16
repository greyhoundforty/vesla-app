#!/bin/bash

set -e

echo "=== Deploying Vesla API Server with Traefik ==="
echo

# Change to server directory
cd /opt/vesla/server

# Stop systemd service if running
if systemctl is-active --quiet vesla-server 2>/dev/null; then
    echo "Stopping systemd service..."
    sudo systemctl stop vesla-server || true
    sudo systemctl disable vesla-server || true
    echo "✓ Stopped systemd service"
else
    echo "ℹ Systemd service not running"
fi

# Stop any manually running gunicorn processes
if pgrep -f "gunicorn.*api:app" > /dev/null; then
    echo "Stopping gunicorn processes..."
    pkill -f "gunicorn.*api:app" || true
    sleep 2
    echo "✓ Stopped gunicorn processes"
fi

# Build Docker image
echo
echo "Building Docker image..."
docker build -t vesla-api:latest .
echo "✓ Built Docker image"

# Stop and remove old container if exists
if docker ps -a --format '{{.Names}}' | grep -q '^vesla-api$'; then
    echo
    echo "Removing old container..."
    docker rm -f vesla-api || true
    echo "✓ Removed old container"
fi

# Deploy with docker-compose
echo
echo "Deploying with Docker Compose..."
docker compose up -d
echo "✓ Deployed container"

# Wait for container to be healthy
echo
echo "Waiting for API to be ready..."
sleep 3

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q '^vesla-api$'; then
    echo "✓ Container is running"

    # Test health endpoint
    echo
    echo "Testing API health endpoint..."
    for i in {1..10}; do
        if docker exec vesla-api curl -s http://localhost:5001/health > /dev/null 2>&1; then
            echo "✓ API is healthy"
            break
        else
            if [ $i -eq 10 ]; then
                echo "✗ API health check failed after 10 attempts"
                echo
                echo "Container logs:"
                docker logs vesla-api --tail 20
                exit 1
            fi
            echo "  Waiting for API to start (attempt $i/10)..."
            sleep 2
        fi
    done
else
    echo "✗ Container is not running"
    exit 1
fi

# Show container info
echo
echo "=== Deployment Complete ==="
echo
echo "Container status:"
docker ps | grep vesla-api
echo
echo "API should be accessible at:"
echo "  - Local: http://localhost:5001/health"
echo "  - Public: https://api.vesla-app.site/health (once DNS propagates)"
echo
echo "View logs:"
echo "  docker logs -f vesla-api"
echo
echo "API Token (for CLI):"
grep "api_token:" config.yaml | awk '{print $2}' | tr -d '"'
echo
