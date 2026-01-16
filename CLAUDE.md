# CLAUDE.md - Vesla Project Context

**Last Updated:** 2026-01-16  
**Project:** Vesla - Piku-inspired deployment tool with Traefik + Docker  
**Status:** Server setup phase - Traefik running but certificates not working

---

## Project Overview

Vesla is a CLI deployment tool inspired by Piku that allows developers to push applications to a server where they are automatically:
- Built in Docker containers
- Registered with Traefik for HTTPS routing
- Given Let's Encrypt certificates via DNS-01 challenge
- Assigned DNS A records automatically via Digital Ocean API

**Architecture:**
```
Developer (vesla CLI) 
  ↓ vesla push (HTTPS)
Vesla Server API (Flask)
  ↓ builds → Docker containers
  ↓ registers → Traefik (reverse proxy)
  ↓ creates → Digital Ocean DNS records
  ↓ result → HTTPS app at subdomain.domain.com
```

**Tech Stack:**
- Docker + Traefik 2.11 (reverse proxy with automatic HTTPS)
- Digital Ocean DNS (DNS-01 challenge for wildcard certs)
- Python (server API, CLI, DNS management)
- Ubuntu 24.04 server

---

## Current State

### ✅ What's Working

1. **Server hardening complete:**
   - SSH key authentication configured
   - Firewall (UFW) configured (mostly - see issues)
   - Tailscale VPN installed for secure access
   - Docker installed and user in docker group

2. **Traefik running:**
   - Container starts successfully
   - Docker socket accessible (fixed permission issues)
   - Configuration loaded from `/opt/vesla/traefik/traefik.yml`
   - Dashboard accessible via Tailscale (not tested yet)
   - No permission errors on logs or acme.json

3. **DNS configured:**
   - 4 domains pointed to server IP via Digital Ocean
   - manage-dns.py script working for A record creation
   - Test subdomain (test.vesla-app.site) has A record

4. **File structure in place:**
   ```
   /opt/vesla/
   ├── traefik/
   │   ├── docker-compose.yml
   │   ├── traefik.yml
   │   ├── .env (DO token, password hash)
   │   ├── config/
   │   │   └── dashboard.yml
   │   ├── letsencrypt/
   │   │   └── acme.json (600 permissions, owned by 1000:999)
   │   └── logs/
   ├── tools/
   │   └── manage-dns.py
   └── server/ (empty - needs to be built)
   ```

---

## ❌ Current Issues (MUST FIX)

### Issue 1: Docker Compose Variable Warning

**Symptom:**
```
WARN[0000] The "vaRQX5hyIB0yoG" variable is not set. Defaulting to a blank string.
```
Appears 4-5 times when running `docker compose up` or `docker compose logs`.

**What we tried:**
1. ✅ Escaped `$` as `$$` in `.env` file (required for bcrypt hash)
2. ✅ Removed dashboard labels from `docker-compose.yml` (moved to `config/dashboard.yml`)
3. ❌ Warning still persists after restart

**Hypothesis:**
The warning might be coming from:
- A leftover reference in `config/dashboard.yml` using `${VAR}` syntax
- The `.env` file itself having a parsing issue
- A cached Docker Compose config

**Next steps to try:**
1. Check if `config/dashboard.yml` still has `${TRAEFIK_DASHBOARD_PASSWORD_HASH}` instead of hardcoded hash
2. Run `docker compose config` to see the resolved configuration
3. Check if there are multiple `docker-compose.yml` files being loaded
4. Grep for "vaRQX5hyIB0yoG" in all config files to find the source

**Files to inspect:**
- `/opt/vesla/traefik/.env`
- `/opt/vesla/traefik/config/dashboard.yml`
- `/opt/vesla/traefik/docker-compose.yml`

---

### Issue 2: Self-Signed Certificates (CRITICAL)

**Symptom:**
```bash
$ curl -I https://test.vesla-app.site
curl: (60) SSL certificate problem: unable to get local issuer certificate

$ curl -I -k https://test.vesla-app.site
HTTP/2 200  # Works with -k flag, meaning self-signed cert
```

Traefik is serving self-signed certificates instead of Let's Encrypt certificates.

**What we tried:**
1. ✅ Configured Digital Ocean DNS challenge in `traefik.yml`
2. ✅ Set `DO_AUTH_TOKEN` in `.env` file
3. ✅ Fixed permissions on `acme.json` (600, owned by 1000:999)
4. ✅ Created wildcard certificate domains in `entryPoints.websecure.http.tls.domains`
5. ✅ DNS A records exist and propagated (verified with `dig @8.8.8.8`)
6. ❌ Certificates still not being issued by Let's Encrypt

**What we haven't tried:**
1. Enable DEBUG logging in Traefik to see ACME challenge details
2. Verify Digital Ocean API token works: `curl -H "Authorization: Bearer $DO_AUTH_TOKEN" https://api.digitalocean.com/v2/account`
3. Check if `acme.json` has any content (should be JSON with certificates)
4. Check Traefik logs for specific ACME/DNS challenge errors
5. Verify certificate resolver name matches everywhere ("digitalocean")
6. Test if Traefik can write TXT records to Digital Ocean for DNS challenge

**Debugging steps:**
```bash
# 1. Enable debug logging
cd /opt/vesla/traefik
nano traefik.yml
# Change: level: INFO → level: DEBUG

# 2. Restart and watch for ACME errors
docker compose down && docker compose up -d
docker compose logs -f | grep -E "acme|certificate|digitalocean|error"

# 3. Check acme.json content
cat letsencrypt/acme.json
# Should have JSON structure with certificates, not empty {}

# 4. Test DO API token
source .env
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account
# Should return account info, not 401 error

# 5. Check certificate resolver config
docker exec traefik cat /etc/traefik/traefik.yml | grep -A 15 "certificatesResolvers"

# 6. Manually verify DNS works
dig @8.8.8.8 test.vesla-app.site +short
# Should return server IP
```

**Possible root causes:**
1. Digital Ocean API token invalid or lacks DNS write permissions
2. DNS challenge timing out before TXT record propagates
3. Certificate resolver name mismatch between `traefik.yml` and container labels
4. Let's Encrypt rate limiting (check https://crt.sh/?q=vesla-app.site)
5. Traefik can't write to Digital Ocean DNS (permissions issue)
6. Wrong DO_AUTH_TOKEN format in environment

**Configuration to verify:**

`traefik.yml` should have:
```yaml
certificatesResolvers:
  digitalocean:
    acme:
      email: "real-email@example.com"  # Must be real email
      storage: "/letsencrypt/acme.json"
      dnsChallenge:
        provider: digitalocean
        delayBeforeCheck: 0
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
```

Container labels should reference:
```yaml
--label "traefik.http.routers.NAME.tls.certresolver=digitalocean"
```

`.env` should have:
```bash
DO_AUTH_TOKEN=dop_v1_actual_token_here_no_quotes
```

---

### Issue 3: Incomplete UFW Firewall Rules

**Symptom:**
Two firewall rules were not properly applied:

1. **ICMP (ping) rule failed** during firewall setup:
   ```
   ERROR: Unsupported protocol 'icmp'
   ```

2. **Vesla Server API port not opened** - will need port 5001 or similar for the API

**What we tried:**
1. ✅ Fixed ICMP syntax from `ufw allow from any to any proto icmp` to `ufw allow in proto icmp`
2. ✅ Updated `configure-firewall.sh` script with fix
3. ❌ Never re-ran the script to apply the ICMP fix
4. ❌ Haven't opened port for Vesla Server API yet

**Current firewall state:**
```bash
$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    YOUR_IP_ADDRESS
22/tcp                     ALLOW IN    100.64.0.0/10
22/tcp                     LIMIT IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
# ⚠️ Missing ICMP rule
# ⚠️ Missing Vesla API port (5001)
```

**What needs to be done:**
```bash
# 1. Add ICMP rule (allow ping from specific IP only for security)
sudo ufw allow from YOUR_IP_ADDRESS proto icmp comment 'ICMP from admin'
sudo ufw allow from 100.64.0.0/10 proto icmp comment 'ICMP from Tailscale'

# 2. Add Vesla Server API port (only from localhost - accessed via Traefik)
# The API should NOT be directly accessible from internet
# Traefik will handle HTTPS and forward to localhost:5001

# 3. Verify rules
sudo ufw status numbered
```

**Important:** The Vesla Server API should listen on `127.0.0.1:5001` (localhost only) and be accessed via Traefik at `https://api.vesla-app.site`. This means we DON'T need to open port 5001 in UFW - Traefik will proxy to it internally.

---

## What We Learned (Important for Next Steps)

### Docker Permissions
- Traefik needs to run as a user that can access Docker socket
- Solution: `user: "1000:999"` where 999 is the docker group ID
- Check with: `getent group docker | cut -d: -f3`

### Bcrypt Password Hash Escaping
- `htpasswd -nbB` generates hash with `$` characters
- In `.env` file: Must escape as `$$` (e.g., `$$2y$$05$$abc...`)
- In YAML file: Use the actual hash with `$$` escaping
- Don't use environment variables in file provider configs (they don't expand)

### Traefik Configuration Split
- **Static config** (`traefik.yml`): Entry points, certificate resolvers, providers
- **Dynamic config** (`config/dashboard.yml`): Routers, middlewares, services
- **Labels** (in `docker-compose.yml`): Per-container routing rules
- Dashboard can be configured via labels OR file provider, not both

### Let's Encrypt DNS Challenge
- Requires `DO_AUTH_TOKEN` environment variable
- Token must have write permissions for DNS
- Traefik creates TXT records like `_acme-challenge.example.com`
- DNS propagation must complete before validation (usually 1-2 minutes)
- Rate limits: 50 certs per week per domain

### File Permissions
- `acme.json` must be 600 permissions
- Must be owned by the user Traefik runs as (1000:999)
- Log directories need write permissions for that user

---

## Next Steps (Priority Order)

### 1. Fix Certificate Issue (CRITICAL - blocks everything)
**Goal:** Get Let's Encrypt certificates working so apps have valid HTTPS

**Steps:**
1. Enable DEBUG logging in `traefik.yml`
2. Restart Traefik and watch logs for ACME errors
3. Verify DO API token: `curl -H "Authorization: Bearer $DO_AUTH_TOKEN" https://api.digitalocean.com/v2/account`
4. Check `acme.json` has content: `cat /opt/vesla/traefik/letsencrypt/acme.json | jq .`
5. If empty, check Traefik can create TXT records in Digital Ocean
6. If rate limited, use staging: `caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"`

**Success criteria:**
- `curl -I https://test.vesla-app.site` returns 200 without `-k` flag
- Certificate issuer is Let's Encrypt: `openssl s_client -connect test.vesla-app.site:443 | grep issuer`
- `acme.json` contains certificate data

### 2. Fix Docker Compose Warning (minor annoyance)
**Goal:** Clean up the variable warning messages

**Steps:**
1. Run `docker compose config` to see resolved config
2. Check if `config/dashboard.yml` still has `${TRAEFIK_DASHBOARD_PASSWORD_HASH}`
3. Replace with actual hash value (with `$$` escaping)
4. Grep all files for "vaRQX5hyIB0yoG" to find source
5. Remove or fix the reference

**Success criteria:**
- `docker compose up -d` shows no warnings
- `docker compose logs` shows no variable warnings

### 3. Fix Firewall Rules (security)
**Goal:** Complete the firewall configuration

**Steps:**
1. Add ICMP rules for admin IP and Tailscale
2. Verify no other ports need to be opened
3. Document that Vesla API will use Traefik proxy (no direct port access)

**Success criteria:**
- Can ping server from admin IP: `ping SERVER_IP`
- `sudo ufw status numbered` shows ICMP rules

### 4. Build Vesla Server API (next major milestone)
**Goal:** Create the Flask API that receives `vesla push` deployments

**Components needed:**
1. **`/opt/vesla/server/api.py`** - Flask app with `/api/deploy` endpoint
2. **`/opt/vesla/server/builder.py`** - Docker build orchestration
3. **`/opt/vesla/server/deployer.py`** - Container deployment with Traefik labels
4. **`/opt/vesla/server/config.yaml`** - Server configuration
5. **`/opt/vesla/server/requirements.txt`** - Python dependencies

**Workflow:**
```
POST /api/deploy
  ↓ Receive tarball + vesla.yaml
  ↓ Extract to temp directory
  ↓ Detect runtime (Python/Node/Dockerfile)
  ↓ Generate Dockerfile if needed
  ↓ docker build -t app:latest .
  ↓ Create DNS A record (manage-dns.py)
  ↓ docker run with Traefik labels
  ↓ Wait for Traefik to get certificate
  ↓ Return deployment URL
```

**See:** Section below for detailed API specification

---

## Vesla Server API Specification

### Endpoint: POST /api/deploy

**Authentication:** Bearer token in header
```
Authorization: Bearer <api_token_from_config>
```

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Fields:
  - `code`: File upload (tarball .tar.gz)
  - `config`: Text field (vesla.yaml as string)

**vesla.yaml format:**
```yaml
app: myapp
domain: myapp.vesla-app.site
runtime: python  # python, node, static, dockerfile
env:
  PORT: 5000
  DEBUG: false
health_check: /health  # optional
resources:  # optional
  memory: 512M
  cpus: 0.5
```

**Response (200 OK):**
```json
{
  "status": "success",
  "app": "myapp",
  "url": "https://myapp.vesla-app.site",
  "container_id": "abc123...",
  "build_time": 45.2,
  "message": "Deployment successful"
}
```

**Response (400/500 Error):**
```json
{
  "status": "error",
  "error": "Build failed: No Dockerfile found and runtime not detected",
  "details": "..."
}
```

### Build Process

**Runtime Detection:**
1. Check if `Dockerfile` exists → use it
2. Check for `requirements.txt` or `pyproject.toml` → Python
3. Check for `package.json` → Node.js
4. Check for `index.html` → Static site
5. Else → Error, runtime not detected

**Generated Dockerfile Examples:**

**Python:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

**Node:**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
CMD ["npm", "start"]
```

**Static:**
```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
```

### Deployment Process

**Docker run command:**
```bash
docker run -d \
  --name <app-name> \
  --network vesla-network \
  --restart unless-stopped \
  -e PORT=<port> \
  -e DEBUG=<debug> \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.<app>.rule=Host(\`<domain>\`)" \
  --label "traefik.http.routers.<app>.entrypoints=websecure" \
  --label "traefik.http.routers.<app>.tls.certresolver=digitalocean" \
  --label "traefik.http.services.<app>.loadbalancer.server.port=<port>" \
  <app>:latest
```

**DNS record creation:**
```bash
cd /opt/vesla/tools
./manage-dns.py create <subdomain> <base-domain> <server-ip>
```

---

## Files Reference

### Configuration Files

**`/opt/vesla/traefik/.env`**
```bash
DO_AUTH_TOKEN=dop_v1_xxxxx
TRAEFIK_DASHBOARD_PASSWORD_HASH=admin:$$2y$$05$$xxxxx
```

**`/opt/vesla/traefik/traefik.yml`**
- Entry points (web :80, websecure :443, metrics :8082)
- Certificate resolver (digitalocean with DNS challenge)
- Docker provider config
- Logging config

**`/opt/vesla/traefik/docker-compose.yml`**
- Traefik container definition
- Port mappings
- Volume mounts
- Network: vesla-network

**`/opt/vesla/traefik/config/dashboard.yml`**
- Dashboard router config
- Basic auth middleware (hardcoded hash)

**`/opt/vesla/server/config.yaml`** (to be created)
```yaml
allowed_domains:
  - "vesla-app.site"
  - "vesla-dev.site"
  - "vesla-staging.site"
  - "vesla-prod.site"

api_token: "<generate: openssl rand -hex 32>"

digitalocean:
  api_token: "${DIGITALOCEAN_TOKEN}"

docker:
  network: "vesla-network"

build:
  max_build_time: 600
  default_memory_limit: "512m"
  default_cpu_limit: "0.5"

server:
  host: "0.0.0.0"
  port: 5001
```

### Scripts

**`/opt/vesla/tools/manage-dns.py`**
```bash
# Create A record
./manage-dns.py create myapp vesla-app.site 1.2.3.4

# Delete A record
./manage-dns.py delete myapp vesla-app.site

# List all A records
./manage-dns.py list vesla-app.site

# Verify DNS propagation
./manage-dns.py verify myapp.vesla-app.site 1.2.3.4
```

---

## Environment Variables

**Required on server:**
```bash
# In /opt/vesla/traefik/.env
DO_AUTH_TOKEN=dop_v1_xxxxx                    # Digital Ocean API token
TRAEFIK_DASHBOARD_PASSWORD_HASH=admin:$$2y$$05$$xxxxx  # Bcrypt hash

# Export for scripts
export DIGITALOCEAN_TOKEN="$DO_AUTH_TOKEN"
```

**Generate API token:**
```bash
openssl rand -hex 32
```

**Generate password hash:**
```bash
htpasswd -nbB admin your_password
# Output: admin:$2y$05$xxxxx
# In .env: admin:$$2y$$05$$xxxxx (double the $)
```

---

## Testing Commands

### Test Traefik
```bash
cd /opt/vesla/traefik

# Check status
docker compose ps

# View logs
docker compose logs -f traefik

# Check for errors
docker compose logs traefik | grep -i error

# View config Traefik loaded
docker exec traefik cat /etc/traefik/traefik.yml
```

### Test Certificates
```bash
# Check acme.json has content
cat /opt/vesla/traefik/letsencrypt/acme.json | jq .

# Test HTTPS endpoint
curl -I https://test.vesla-app.site

# View certificate details
echo | openssl s_client -servername test.vesla-app.site \
  -connect YOUR_SERVER_IP:443 2>/dev/null | \
  openssl x509 -noout -issuer -dates
```

### Test DNS
```bash
# Check DNS resolution
dig @8.8.8.8 test.vesla-app.site +short

# List all records
cd /opt/vesla/tools
./manage-dns.py list vesla-app.site
```

### Test Digital Ocean API
```bash
source /opt/vesla/traefik/.env

# Test account access
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account

# Test domain access
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/domains
```

---

## Known Gotchas

1. **Dollar signs in bcrypt hashes:** Must be escaped as `$$` in `.env` and YAML files
2. **File provider doesn't expand env vars:** Hardcode values in `config/dashboard.yml`
3. **Certificate resolver name must match:** Same name in `traefik.yml` and container labels
4. **DNS propagation takes time:** Wait 1-2 minutes after creating A record
5. **acme.json permissions:** Must be 600 and owned by Traefik user (1000:999)
6. **Docker socket permissions:** User must be in docker group
7. **Let's Encrypt rate limits:** 50 certs/week per domain - use staging for testing
8. **Traefik dashboard config:** Use file provider OR labels, not both

---

## Troubleshooting Guide

### Problem: Traefik won't start
```bash
docker compose logs traefik
# Look for: YAML errors, permission denied, port conflicts
```

**Common causes:**
- Port 80/443 already in use: `sudo lsof -i :80`
- Invalid YAML syntax: `yamllint traefik.yml`
- Wrong permissions: `chmod 600 letsencrypt/acme.json`

### Problem: Self-signed certificates
```bash
# Enable debug logging
# In traefik.yml: level: DEBUG
docker compose restart

# Watch for ACME errors
docker compose logs -f | grep -i acme
```

**Common causes:**
- DO token invalid
- DNS not propagated
- Rate limited by Let's Encrypt
- Wrong certificate resolver name

### Problem: Container can't be reached
```bash
# Check container is running
docker ps | grep myapp

# Check Traefik can see it
docker exec traefik cat /etc/traefik/traefik.yml

# Check DNS
dig @8.8.8.8 myapp.vesla-app.site +short
```

**Common causes:**
- Container not on vesla-network
- Missing `traefik.enable=true` label
- Wrong port in loadbalancer label
- DNS not created/propagated

---

## Quick Start for Next Agent

1. **Read this file completely** - especially "Current Issues" section
2. **Priority: Fix certificate issue** - blocks all other work
3. **Start with debug logging:**
   ```bash
   cd /opt/vesla/traefik
   nano traefik.yml  # Change level: INFO → level: DEBUG
   docker compose restart
   docker compose logs -f | tee /tmp/debug.log
   ```
4. **Check the debug log** for ACME/certificate/DNS errors
5. **Verify DO token works:** `curl -H "Authorization: Bearer $DO_AUTH_TOKEN" https://api.digitalocean.com/v2/account`
6. **Once certs work**, move to building Vesla Server API

---

## Resources

- Traefik Docs: https://doc.traefik.io/traefik/
- Let's Encrypt DNS Challenge: https://letsencrypt.org/docs/challenge-types/#dns-01-challenge
- Digital Ocean API: https://docs.digitalocean.com/reference/api/
- Docker SDK: https://docker-py.readthedocs.io/

---

## Contact / Handoff Notes

**Server Access:**
- SSH: `ssh vesla@SERVER_IP` (key auth only)
- Tailscale: `ssh vesla@100.x.x.x`

**Important IPs:**
- Server: (ask user)
- Admin IP: (ask user)
- Tailscale: `tailscale ip -4` on server

**Domains configured:**
- vesla-app.site
- vesla-dev.site
- vesla-staging.site
- vesla-prod.site

**Credentials:**
- DO API token: In `/opt/vesla/traefik/.env`
- Traefik dashboard: In `/opt/vesla/traefik/.env`
- Vesla API token: Generate with `openssl rand -hex 32`

---

**Good luck! The foundation is solid, just need to get those certificates working. 🚀**
