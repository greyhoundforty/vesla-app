# Portainer Deployment

Portainer provides real-time container monitoring and log aggregation for all Docker containers on the Vesla server.

## Quick Start

```bash
cd /opt/vesla/portainer
docker compose up -d
```

## Access via Tailscale

Expose Portainer through Tailscale for secure remote access:

```bash
tailscale serve https / http://127.0.0.1:9000
```

Then access at: `https://YOUR_TAILSCALE_IP/`

## Features

- Container status monitoring
- Real-time log viewing with search and filtering
- Container restart/stop/remove operations
- Resource usage stats (CPU, memory, network)
- Image management
- Volume and network inspection
- Multi-user support with role-based access

## Security

- Only binds to localhost (127.0.0.1:9000)
- Access via Tailscale provides encrypted tunnel
- Initial password setup required on first access
- No direct exposure to internet

## Cleanup

To remove Portainer:

```bash
docker compose down -v  # -v also removes the data volume
```
