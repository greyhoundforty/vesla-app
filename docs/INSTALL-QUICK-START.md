# Server Installation Quick Start

## TL;DR

```bash
# On a fresh Ubuntu 24.04 server
ssh root@your-server-ip

# Download and run
curl -O https://raw.githubusercontent.com/yourusername/vesla-app/main/install-server.sh
sudo bash install-server.sh

# Follow the prompts (takes 5-10 minutes)
# Then verify:
bash /opt/vesla/scripts/verify-installation.sh
```

## What You'll Be Asked

1. **Domain names** - `vesla-app.site,vesla-app.com`
2. **DigitalOcean API token** - From https://cloud.digitalocean.com/account/api/tokens
3. **Email for Let's Encrypt** - For certificate notifications
4. **Dashboard password** - For admin access to Traefik
5. **Install Tailscale?** - (optional) Secure VPN access
6. **Install Portainer?** - (optional) Docker web UI

## Files Created

| File | Purpose |
|------|---------|
| `install-server.sh` | Main installation script |
| `scripts/setup-traefik.sh` | Traefik configuration generator |
| `scripts/setup-api-server.sh` | API server setup helper |
| `scripts/verify-installation.sh` | Verification and testing |
| `INSTALL-SERVER-README.md` | Full documentation |
| `.env.template` | Environment variable reference |

## Key Features

- ✓ Colored output with clear prompts
- ✓ Well-spaced, readable formatting
- ✓ All output logged to `/opt/vesla/install.log`
- ✓ Prerequisite validation (OS, disk space, internet, etc.)
- ✓ Idempotent design (safe to re-run)
- ✓ Error handling with detailed messages
- ✓ Container health verification
- ✓ Success report with next steps

## After Installation

### 1. Save Your Credentials

```bash
# These files contain secrets - back them up securely
cat /opt/vesla/traefik/.env
cat /opt/vesla/server/.env
```

### 2. Configure Your DNS

Verify that each domain has an A record pointing to your server:

```bash
dig your-domain.com
# Should show your server's IP address
```

### 3. Configure the CLI

On your local machine:

```bash
# From the server, get your API token
cat /opt/vesla/server/.env | grep API_TOKEN

# Then configure:
vesla config set server_url https://api.your-domain.com
vesla config set api_token <token-from-above>

# Verify:
vesla config list
```

### 4. Test Deployment

```bash
cd example-apps/python
vesla push

# Wait 1-2 minutes, then:
curl https://example-python.your-domain.com/health
```

## Troubleshooting

### Installation fails
```bash
# Check the log
tail -100 /opt/vesla/install.log

# Try again
sudo bash /opt/vesla/install-server.sh
```

### Containers won't start
```bash
# Check Docker
systemctl status docker

# Check logs
docker compose -f /opt/vesla/traefik/docker-compose.yml logs
docker compose -f /opt/vesla/server/docker-compose.yml logs
```

### API not responding
```bash
# Check it's running
docker ps | grep vesla-api

# Test directly
curl -v http://127.0.0.1:5001/health
```

### Certificates not generating
```bash
# Check DigitalOcean token works
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.digitalocean.com/v2/account

# Check DNS propagation
dig @8.8.8.8 your-domain.com
```

## Manual Tasks Still Required

1. **Configure DNS A records** in DigitalOcean (points to server IP)
2. **Create CLI config** on your local machine
3. **Deploy test apps** to verify everything works
4. **Set up backups** for certificates and tarballs
5. **Configure multi-provider DNS** (if needed) - see Task 2

## Files & Logs

| Location | Purpose |
|----------|---------|
| `/opt/vesla/install.log` | Installation log (check for errors) |
| `/opt/vesla/traefik/.env` | Traefik secrets (keep secure!) |
| `/opt/vesla/server/.env` | API secrets (keep secure!) |
| `/opt/vesla/traefik/traefik.yml` | Traefik configuration |
| `/opt/vesla/traefik/letsencrypt/acme.json` | SSL certificates |

## Next Steps

Once installation is complete:

1. **For admin access:**
   ```bash
   # Traefik dashboard
   ssh -L 8080:localhost:8080 user@server-ip
   # Then visit: http://localhost:8080/dashboard/
   
   # Vesla dashboard
   ssh -L 5002:localhost:5002 user@server-ip
   # Then visit: http://localhost:5002
   ```

2. **For remote developers:**
   ```bash
   # After configuring CLI
   vesla push  # From any project with vesla.yaml
   vesla list
   vesla logs myapp
   ```

3. **Plan for production:**
   - Implement Task 2 (multi-provider DNS support)
   - Implement Task 3 (backup mechanism)
   - Configure monitoring
   - Set up incident response

---

**Questions?** See `INSTALL-SERVER-README.md` for detailed documentation.
