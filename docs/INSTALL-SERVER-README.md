#!/bin/bash

################################################################################
# Vesla Server Installation - README
# Detailed documentation for the installation process
################################################################################

# Vesla Server Installation Guide

## Overview

This guide walks through installing Vesla on a new Ubuntu 24.04 server. The `install-server.sh` script automates the entire process.

## Prerequisites

### Hardware Requirements
- Ubuntu 24.04 LTS (minimal or standard installation)
- 2GB RAM minimum (4GB+ recommended)
- 10GB disk space minimum (20GB+ recommended)
- Static public IP address
- Inbound ports 22, 80, 443 open

### External Requirements
- DigitalOcean account with API token
- Domain name(s) configured in DigitalOcean DNS
- Email address for Let's Encrypt certificate renewal notifications

### Permissions
- Root or sudo access on the server
- Internet connectivity (download Docker, packages, code)

## Quick Installation

### 1. Connect to Your Server

```bash
ssh root@your-server-ip
```

### 2. Download Installation Script

```bash
curl -O https://raw.githubusercontent.com/yourusername/vesla-app/main/install-server.sh
chmod +x install-server.sh
```

### 3. Run Installation

```bash
sudo bash install-server.sh
```

### 4. Follow Interactive Prompts

The script will ask for:
- **Domain names**: Comma-separated list (e.g., `vesla-app.site,vesla-app.com`)
- **DigitalOcean API token**: From https://cloud.digitalocean.com/account/api/tokens
- **Email address**: For Let's Encrypt notifications
- **Dashboard password**: For Traefik dashboard access
- **Optional features**: Tailscale, Portainer

### 5. Wait for Installation

The script will:
- Check prerequisites
- Install Docker & Docker Compose
- Create system user and directories
- Download Vesla repository
- Generate configuration files
- Start containers
- Verify installation

Typical installation time: 5-10 minutes

## What Gets Installed

### System Components
- Docker Engine (latest stable)
- Docker Compose (v2.23.0+)
- Vesla user account (non-root)
- UFW firewall rules (open 22, 80, 443)
- Optional: Tailscale VPN
- Optional: Portainer UI

### Vesla Components
- **Traefik 2.11** - Reverse proxy and HTTPS termination (port 443, 80)
- **Vesla API Server** - REST API for deployments (port 5001)
- **Vesla Dashboard** - Web UI for management (port 5002)
- **Portainer** (optional) - Docker management UI (port 9000)

### Directory Structure

```
/opt/vesla/
├── install.log                 # Installation log
├── traefik/
│   ├── docker-compose.yml
│   ├── traefik.yml            # Configuration (generated)
│   ├── .env                   # API token, passwords (generated, keep secure!)
│   ├── config/
│   │   ├── dashboard.yml
│   │   └── vesla-api.yml
│   └── letsencrypt/
│       └── acme.json          # SSL certificates
├── server/
│   ├── docker-compose.yml
│   ├── .env                   # Server secrets (generated, keep secure!)
│   ├── api.py
│   ├── builder.py
│   ├── deployer.py
│   └── dns_manager.py
├── dashboard/
│   ├── docker-compose.yml
│   └── app.py
└── portainer/ (if installed)
    └── docker-compose.yml
```

## Configuration Files

### Traefik Configuration (`traefik/.env`)

Generated automatically with:
- `DO_AUTH_TOKEN` - DigitalOcean API token
- `ACME_EMAIL` - Let's Encrypt email
- `TRAEFIK_DASHBOARD_PASSWORD_HASH` - Bcrypt hash of dashboard password

**Keep this file secure!** It contains sensitive credentials.

### API Server Configuration (`server/.env`)

Generated automatically with:
- `FLASK_ENV` - Set to production
- `API_TOKEN` - Random 32-byte token for CLI authentication
- `DO_AUTH_TOKEN` - DigitalOcean API token (copy from Traefik)
- `ACME_EMAIL` - Let's Encrypt email

**Keep this file secure!**

## Post-Installation

### 1. Configure CLI

On your local machine:

```bash
# Get the API token from the server's .env file
cat /opt/vesla/server/.env | grep API_TOKEN

# Configure the CLI
vesla config set server_url https://api.your-domain.com
vesla config set api_token <the-token-you-got>

# Verify configuration
vesla config list
```

### 2. Set Up DNS Records

Verify that DNS A records point your domains to your server's IP:

```bash
# For each domain, check:
dig your-domain.com
dig your-other-domain.com

# Should show your server's IP address
```

### 3. Test Deployment

Deploy a test application:

```bash
cd example-apps/python
vesla push
```

After 1-2 minutes, visit: `https://example-python.your-domain.com`

### 4. Access Dashboards

#### Traefik Dashboard (admin only)
```bash
# Via SSH tunnel (secure)
ssh -L 8080:localhost:8080 user@server-ip

# Then open: http://localhost:8080/dashboard/
# Username: admin
# Password: <the one you set>
```

#### Vesla Dashboard
```bash
ssh -L 5002:localhost:5002 user@server-ip
# Then open: http://localhost:5002
```

#### Portainer (if installed)
```bash
ssh -L 9000:localhost:9000 user@server-ip
# Then open: http://localhost:9000
# Set up initial password on first access
```

#### Tailscale Access (if installed)
```bash
# On the server
tailscale up

# On your local machine
tailscale serve https / http://server-tailscale-ip:5002

# Then access: https://your-tailscale-ip/
```

## Troubleshooting

### Check Installation Status

```bash
# View installation log
tail -100 /opt/vesla/install.log

# Check running containers
docker ps

# Check Docker logs
docker compose -f /opt/vesla/traefik/docker-compose.yml logs
docker compose -f /opt/vesla/server/docker-compose.yml logs
```

### Common Issues

#### Containers won't start
```bash
# Check system resources
free -h
df -h

# Check Docker daemon
systemctl status docker

# View detailed logs
docker compose -f /opt/vesla/traefik/docker-compose.yml logs traefik
```

#### API unreachable
```bash
# Verify firewall
ufw status

# Test port connectivity
curl -I http://127.0.0.1:5001/health

# Check DNS
dig api.your-domain.com
```

#### Certificate issues
```bash
# Check Traefik logs for ACME errors
docker compose -f /opt/vesla/traefik/docker-compose.yml logs traefik | grep -i acme

# Verify DigitalOcean API token works
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.digitalocean.com/v2/account
```

#### Docker network issues
```bash
# Verify network exists
docker network inspect vesla-network

# Verify container connectivity
docker exec vesla-api curl http://127.0.0.1:5001/health
```

## Security Recommendations

1. **Protect `.env` files**
   ```bash
   # Already set to 600, but verify:
   ls -la /opt/vesla/traefik/.env
   ls -la /opt/vesla/server/.env
   ```

2. **Enable SSH key authentication only**
   ```bash
   # Edit SSH config (as root)
   # Set: PasswordAuthentication no
   # Set: PermitRootLogin no
   systemctl restart ssh
   ```

3. **Configure UFW properly**
   ```bash
   ufw status
   # Should allow: 22/tcp, 80/tcp, 443/tcp
   ```

4. **Use Tailscale for admin access**
   - Encrypts all traffic
   - Avoids exposing management interfaces
   - Easy to revoke access

5. **Backup credentials**
   ```bash
   # Securely backup .env files
   tar czf vesla-config-backup.tar.gz /opt/vesla/.env /opt/vesla/*/.env
   # Store in secure location (password manager, encrypted backup, etc.)
   ```

## Rollback / Reinstall

If you need to reinstall or redo configuration:

```bash
# Stop all containers
cd /opt/vesla/traefik && docker compose down
cd /opt/vesla/server && docker compose down
cd /opt/vesla/dashboard && docker compose down

# Remove volumes (careful - this deletes data!)
docker volume rm traefik_data portainer_data

# Re-run installation
sudo bash /opt/vesla/install-server.sh

# Or manually reconfigure
cd /opt/vesla
bash scripts/setup-traefik.sh
bash scripts/setup-api-server.sh
```

## Manual Installation (Alternative)

If the script fails, you can manually complete these steps:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
bash /tmp/get-docker.sh

# 2. Create vesla user
useradd -m -s /bin/bash -u 1000 vesla
usermod -aG docker vesla

# 3. Clone repository
mkdir -p /opt/vesla
git clone <repo-url> /opt/vesla
chown -R vesla:vesla /opt/vesla

# 4. Create network
docker network create --driver bridge --subnet=172.18.0.0/16 vesla-network

# 5. Create .env files (manually add credentials)
nano /opt/vesla/traefik/.env
nano /opt/vesla/server/.env

# 6. Start containers
cd /opt/vesla/traefik && docker compose up -d
cd /opt/vesla/server && docker compose up -d
cd /opt/vesla/dashboard && docker compose up -d
```

## Support & Documentation

- **Main README**: See main project README for overview
- **CLI Help**: `vesla --help`
- **API Documentation**: See server/QUICKSTART.md
- **Build System**: See server/BUILDPACKS.md
- **DNS Setup**: See server/dns_manager.py

## Next Steps

1. Deploy your first application: `vesla push`
2. Monitor deployments: Check dashboards
3. Set up backups: Configure object storage
4. Plan CI/CD integration: Auto-deploy on push

---

**Last Updated:** January 2026
**Vesla Version:** 0.1.0
