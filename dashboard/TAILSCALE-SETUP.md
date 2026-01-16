# Vesla Dashboard - Tailscale Serve Setup

The Vesla Dashboard is configured to be accessible **ONLY via Tailscale** for maximum security. It is never exposed to the public internet.

## Architecture

```
Tailscale Network (100.x.x.x)
  ↓ Encrypted WireGuard tunnel
Tailscale Serve (HTTPS proxy)
  ↓ localhost only
Dashboard Container (127.0.0.1:5002)
  ↓ Docker socket
Docker Engine
```

## Security Features

1. **No Public Access**: Dashboard is bound to `127.0.0.1:5002` (localhost only)
2. **No Traefik Routing**: Dashboard is NOT registered with Traefik
3. **No DNS Record**: No public DNS pointing to the dashboard
4. **Tailscale Only**: Accessible exclusively via Tailscale's encrypted network
5. **UFW Friendly**: No special firewall rules needed (Tailscale handles routing)

## Setup Instructions

### 1. Run the Setup Script

```bash
cd /opt/vesla/dashboard
chmod +x setup-tailscale-serve.sh
./setup-tailscale-serve.sh
```

This script will:
- Set your user as a Tailscale operator (requires sudo once)
- Configure Tailscale Serve to expose port 5002
- Display your dashboard's Tailscale URL

### 2. Manual Setup (Alternative)

If you prefer to run commands manually:

```bash
# Set operator (one-time, requires sudo)
sudo tailscale set --operator=$USER

# Configure Tailscale Serve
tailscale serve --bg 5002

# Check status
tailscale serve status
```

### 3. Get Your Dashboard URL

```bash
# View your Tailscale hostname
tailscale status

# Your dashboard will be at:
# https://<hostname>.tail<suffix>.ts.net
# Example: https://srv1.tail84fc1.ts.net
```

## UFW Firewall Rules

**No UFW changes are required!**

Tailscale operates at the network layer and doesn't require opening ports in UFW. The dashboard:
- Binds to `127.0.0.1:5002` (not accessible externally)
- Is proxied by Tailscale Serve over the encrypted WireGuard tunnel
- Never touches ports 80/443 or any publicly accessible ports

Current UFW rules remain unchanged:
```bash
sudo ufw status verbose

# Expected output:
# 22/tcp (SSH) - ALLOW from specific IPs + Tailscale
# 80/tcp (HTTP) - ALLOW from Anywhere (for Traefik/deployed apps)
# 443/tcp (HTTPS) - ALLOW from Anywhere (for Traefik/deployed apps)
# No rule for 5002 (dashboard) - it's localhost only
```

## Accessing the Dashboard

### From Any Device on Your Tailscale Network

1. **Connect to Tailscale** on your device (laptop, phone, tablet)
2. **Open your browser** and navigate to your server's Tailscale hostname:
   ```
   https://srv1.tail84fc1.ts.net
   ```
3. **Enjoy the dashboard!** You'll see the NASA Mission Control interface

### From Your Local Machine (Example)

If your Tailscale tailnet is `tail84fc1.ts.net` and your server is `srv1`:

```bash
# On your laptop (connected to Tailscale)
curl https://srv1.tail84fc1.ts.net/health

# Or open in browser:
# https://srv1.tail84fc1.ts.net
```

## Tailscale Serve Commands

### Check Current Configuration

```bash
tailscale serve status
```

Example output:
```
https://srv1.tail84fc1.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:5002
```

### Stop Serving

```bash
tailscale serve reset
```

This will stop serving the dashboard via Tailscale.

### Restart Serving

```bash
tailscale serve --bg 5002
```

### View All Tailscale Devices

```bash
tailscale status
```

## Container Management

The dashboard runs as a Docker container bound to localhost:

```bash
# View container status
docker ps | grep vesla-dashboard

# View logs
docker logs -f vesla-dashboard

# Restart container
cd /opt/vesla/dashboard
docker compose restart

# Stop container
docker compose down

# Start container
docker compose up -d
```

## Troubleshooting

### Dashboard not accessible

1. **Check container is running**:
   ```bash
   docker ps | grep vesla-dashboard
   ```

2. **Check localhost access**:
   ```bash
   curl http://localhost:5002/health
   # Should return: {"service":"vesla-dashboard","status":"healthy"}
   ```

3. **Check Tailscale Serve configuration**:
   ```bash
   tailscale serve status
   ```

4. **Check Tailscale connection**:
   ```bash
   tailscale status
   # Server should show as "online"
   ```

5. **Restart Tailscale Serve**:
   ```bash
   tailscale serve reset
   tailscale serve --bg 5002
   ```

### "Access denied: serve config denied" Error

Run this once to set your user as a Tailscale operator:
```bash
sudo tailscale set --operator=$USER
```

### Container keeps restarting

Check container logs:
```bash
docker logs vesla-dashboard
```

Common issues:
- Docker socket permission denied → Check volume mount in docker-compose.yml
- Port already in use → Check nothing else is using port 5002

### Can't access from Tailscale device

1. Ensure your device is connected to Tailscale:
   ```bash
   tailscale status
   ```

2. Check you're using HTTPS (not HTTP):
   ```
   https://srv1.tail84fc1.ts.net  ✓
   http://srv1.tail84fc1.ts.net   ✗
   ```

3. Try accessing via IP instead of hostname:
   ```
   https://100.108.35.29
   ```

## Security Notes

### Why Tailscale Serve instead of Traefik?

1. **Zero Public Exposure**: Dashboard never touches the public internet
2. **No DNS Required**: No DNS records that could leak server info
3. **No Certificate Management**: Tailscale handles TLS automatically
4. **No IP Whitelisting**: Don't need to maintain IP lists
5. **Defense in Depth**: Multiple layers of security (Tailscale auth + localhost bind)

### What if Tailscale goes down?

- Dashboard will still run locally on `127.0.0.1:5002`
- Accessible via SSH tunnel if needed:
  ```bash
  ssh -L 5002:localhost:5002 vesla@your-server-ip
  # Then visit http://localhost:5002 in your browser
  ```

### Can I expose it publicly later?

Yes, but not recommended. If you really need public access:

1. **Option A**: Use Tailscale Funnel (Tailscale's public proxy feature)
   ```bash
   tailscale funnel 5002
   ```

2. **Option B**: Re-add Traefik labels to docker-compose.yml
   - Add DNS record
   - Configure Traefik routing
   - Add authentication middleware (basic auth, OAuth, etc.)

## Files

- `/opt/vesla/dashboard/docker-compose.yml` - Container configuration
- `/opt/vesla/dashboard/app.py` - Flask application
- `/opt/vesla/dashboard/templates/index.html` - NASA Mission Control UI
- `/opt/vesla/dashboard/setup-tailscale-serve.sh` - Setup script

## Dashboard Features

- **Real-time deployment monitoring**: See all active Vesla deployments
- **Resource usage**: Memory and CPU stats for each container
- **Uptime tracking**: How long each deployment has been running
- **Direct links**: Click domains to open deployed apps
- **Auto-refresh**: Updates every 30 seconds
- **Retro aesthetics**: 1960s NASA Mission Control design

## Next Steps

After setup:
1. ✓ Dashboard container running
2. ✓ Bound to localhost only
3. Run `./setup-tailscale-serve.sh` to complete setup
4. Access via `https://<your-hostname>.tail<suffix>.ts.net`
5. Enjoy your private Mission Control dashboard!

---

**Questions?** Check the troubleshooting section or container logs.
