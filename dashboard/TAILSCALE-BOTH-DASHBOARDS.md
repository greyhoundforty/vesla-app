# Tailscale Serve Setup for Both Dashboards

This guide shows how to configure Tailscale serve to expose both the Vesla Dashboard and the Traefik Dashboard privately via your Tailscale network.

## Architecture

```
Tailscale Network (100.x.x.x)
  ↓ Encrypted WireGuard tunnel
Tailscale Serve (HTTPS proxy with path-based routing)
  ├─ / → Vesla Dashboard (127.0.0.1:5002)
  └─ /traefik → Traefik Dashboard (127.0.0.1:8080)
```

## Security

Both dashboards are:
- Bound to localhost only (127.0.0.1)
- NOT accessible from the public internet
- NO DNS records pointing to them
- NO open ports in UFW firewall
- ONLY accessible via Tailscale's encrypted WireGuard VPN

## Manual Setup Commands

Run these commands to configure Tailscale serve for both dashboards:

### 1. Set yourself as Tailscale operator (one-time only)

```bash
sudo tailscale set --operator=$USER
```

This allows you to configure Tailscale serve without sudo in the future.

### 2. Configure Vesla Dashboard (root path)

```bash
tailscale serve --bg --set-path=/ http://127.0.0.1:5002
```

This makes the Vesla Dashboard accessible at `https://your-hostname.ts.net/`

### 3. Configure Traefik Dashboard (traefik path)

```bash
tailscale serve --bg --set-path=/traefik http://127.0.0.1:8080
```

This makes the Traefik Dashboard accessible at `https://your-hostname.ts.net/traefik`

### 4. Verify configuration

```bash
tailscale serve status
```

Expected output:
```
https://srv1.tail84fc1.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:5002
|-- /traefik proxy http://127.0.0.1:8080
```

### 5. Get your Tailscale hostname

```bash
tailscale status | grep $(hostname)
```

## Accessing the Dashboards

From any device on your Tailscale network:

1. **Vesla Dashboard (Deployment Overview)**
   ```
   https://srv1.tail84fc1.ts.net/
   ```
   Shows all deployed applications, resource usage, uptime, and health status.

2. **Traefik Dashboard (Proxy Status)**
   ```
   https://srv1.tail84fc1.ts.net/traefik
   ```
   Shows Traefik routing configuration, services, and middlewares.

## Quick Setup Script

Alternatively, run the automated setup script:

```bash
cd /opt/vesla/dashboard
sudo ./setup-all-dashboards.sh
```

This script runs all the commands above automatically.

## Management Commands

### View current configuration
```bash
tailscale serve status
```

### Stop serving both dashboards
```bash
tailscale serve reset
```

### Restart serving
Run steps 2-3 again.

### Test dashboard health
```bash
# Vesla Dashboard
curl http://localhost:5002/health

# Traefik Dashboard
curl http://localhost:8080/api/overview
```

## Troubleshooting

### "Access denied: serve config denied"

Run the operator setup command:
```bash
sudo tailscale set --operator=$USER
```

### Dashboard not loading

1. Check containers are running:
```bash
docker ps | grep -E "vesla-dashboard|traefik"
```

2. Check localhost access:
```bash
curl http://localhost:5002/health    # Vesla Dashboard
curl http://localhost:8080/api/http/routers  # Traefik
```

3. Check Tailscale serve configuration:
```bash
tailscale serve status
```

4. Check Tailscale connection:
```bash
tailscale status
```

### Traefik dashboard asks for authentication

If the Traefik dashboard prompts for credentials, use:
- **Username**: admin
- **Password**: (from `/opt/vesla/traefik/.env` file, TRAEFIK_DASHBOARD_PASSWORD_HASH variable)

To get the password:
```bash
# The password was set during Traefik setup
# Check with the admin who set it up
grep TRAEFIK_DASHBOARD_PASSWORD_HASH /opt/vesla/traefik/.env
```

### 404 Not Found on /traefik

Traefik dashboard requires the path without trailing slash:
```
✓ https://srv1.tail84fc1.ts.net/traefik
✗ https://srv1.tail84fc1.ts.net/traefik/
```

## Files Reference

- `/opt/vesla/dashboard/docker-compose.yml` - Vesla dashboard container config
- `/opt/vesla/traefik/docker-compose.yml` - Traefik container config
- `/opt/vesla/dashboard/setup-all-dashboards.sh` - Automated setup script

## Next Steps

After configuration:
1. ✓ Both dashboards accessible via Tailscale only
2. ✓ No public internet exposure
3. ✓ No UFW changes needed
4. Access dashboards from any Tailscale-connected device
5. Monitor your deployments and proxy configuration securely!
