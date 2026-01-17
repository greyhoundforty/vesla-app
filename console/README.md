# Vesla Console - Skeleton

This is the skeleton application for the Vesla Console, a centralized dashboard for viewing and managing Vesla-deployed applications and system containers.

## Overview

The Vesla Console provides:
- Real-time container status monitoring
- Log aggregation and viewing
- Resource usage statistics (CPU, memory)
- Container management (restart, stop, start)
- Admin and client views (planning phase)

## Development Status

This is a **skeleton implementation** with:
- Backend API endpoints for Docker integration
- Basic frontend template
- Docker Compose setup for server deployment
- Placeholder for advanced features

## Future Enhancements (Planning Phase)

- Advanced filtering and search
- Log streaming with real-time updates
- Metrics graphs (CPU, memory over time)
- Role-based access control (admin vs client)
- Deployment history tracking
- Performance alerts and notifications
- Multi-tenant support

## API Endpoints

All endpoints require proper authentication (to be implemented).

### GET /api/apps
List all Vesla-managed and system containers.

Response:
```json
{
  "apps": [
    {
      "id": "abc123def456",
      "name": "myapp",
      "status": "running",
      "image": "myapp:latest",
      "created": "2026-01-16T10:30:00Z",
      "started": "2026-01-17T08:00:00Z",
      "ports": {...},
      "labels": {...},
      "is_running": true
    }
  ],
  "system": [...],
  "total": 10
}
```

### GET /api/apps/<container_name>/logs?tail=100
Get logs for a specific container.

### GET /api/apps/<container_name>/stats
Get resource usage statistics.

### POST /api/apps/<container_name>/action
Perform actions on containers (restart, stop, start).

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
export FLASK_ENV=development
export PORT=5003

# Run the app
python app.py

# Visit http://localhost:5003
```

## Deployment

On your Vesla server:

```bash
cd /opt/vesla/console
docker compose up -d
```

Then expose via Tailscale:
```bash
tailscale serve https / http://127.0.0.1:5003
```

## Architecture Notes

- Reads-only access to Docker socket (`/var/run/docker.sock:ro`)
- Runs as non-root user (uid 1000)
- Uses Flask for lightweight HTTP server
- Docker Python SDK for container management
- Connected to `vesla-network` for service discovery

## Next Steps (Planning Session)

1. Implement authentication layer
2. Add role-based access control (admin vs app owner)
3. Implement real-time log streaming (WebSocket)
4. Add metrics collection and graphing
5. Implement client view (limited to user's own apps)
6. Add deployment history tracking
7. Implement notification system

---

**Note:** This skeleton requires planning for production use, particularly around authentication and authorization for client access.
