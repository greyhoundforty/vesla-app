# Vesla Project - Current State & Next Steps

**Last Updated:** 2026-01-16
**Purpose:** Quick-start guide for next agent to continue work

---

## TL;DR - What You Need to Know

**Project:** Vesla - Piku-inspired deployment tool (push apps → auto-deploy with HTTPS)

**Current Status:**
- ✅ Traefik running
- ✅ DNS configured
- ❌ **CRITICAL ISSUE:** Self-signed certificates (Let's Encrypt not working)
- ⚠️ Minor: Docker Compose variable warning
- ⚠️ Minor: Incomplete firewall rules

**Your Mission:** Fix the certificate issue so apps get valid HTTPS from Let's Encrypt

---

## Critical Issue: Self-Signed Certificates

### The Problem

```bash
$ curl -I https://test.vesla-app.site
curl: (60) SSL certificate problem: unable to get local issuer certificate

$ curl -I -k https://test.vesla-app.site
HTTP/2 200  # Works with -k flag
```

Traefik is serving **self-signed certificates** instead of Let's Encrypt certificates via DNS-01 challenge.

### What's Been Configured

1. **Digital Ocean DNS Challenge** configured in `/opt/vesla/traefik/traefik.yml`:
   ```yaml
   certificatesResolvers:
     digitalocean:
       acme:
         email: "real-email@example.com"
         storage: "/letsencrypt/acme.json"
         dnsChallenge:
           provider: digitalocean
           delayBeforeCheck: 0
           resolvers:
             - "1.1.1.1:53"
             - "8.8.8.8:53"
   ```

2. **DO_AUTH_TOKEN** set in `/opt/vesla/traefik/.env`

3. **acme.json** has correct permissions:
   - 600 permissions
   - Owned by 1000:999 (Traefik user)

4. **DNS A record exists** and propagated:
   - test.vesla-app.site → server IP
   - Verified with `dig @8.8.8.8 test.vesla-app.site`

5. **Wildcard domains** configured in traefik.yml:
   ```yaml
   entryPoints:
     websecure:
       http:
         tls:
           domains:
             - main: "vesla-app.site"
               sans:
                 - "*.vesla-app.site"
             # + 3 more domains
   ```

### What Hasn't Been Tried Yet

**THESE ARE YOUR NEXT STEPS:**

1. **Enable DEBUG logging** to see ACME errors:
   ```bash
   cd /opt/vesla/traefik
   nano traefik.yml
   # Change: level: INFO → level: DEBUG
   docker compose restart
   docker compose logs -f | grep -E "acme|certificate|digitalocean|error"
   ```

2. **Verify DO API token works**:
   ```bash
   source /opt/vesla/traefik/.env
   curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
     https://api.digitalocean.com/v2/account
   # Should return account info, not 401
   ```

3. **Check acme.json has content**:
   ```bash
   cat /opt/vesla/traefik/letsencrypt/acme.json
   # Should have JSON structure, not empty {}
   ```

4. **Verify certificate resolver name matches everywhere**:
   ```bash
   # In traefik.yml: certificatesResolvers.digitalocean
   # In container labels: tls.certresolver=digitalocean
   docker exec traefik cat /etc/traefik/traefik.yml | grep -A 10 certificatesResolvers
   ```

5. **Check Let's Encrypt rate limiting**:
   - Visit: https://crt.sh/?q=vesla-app.site
   - If many certs issued, switch to staging:
     ```yaml
     caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"
     ```

6. **Test if Traefik can create TXT records**:
   - Watch logs during restart
   - Look for DNS challenge attempts
   - Check if `_acme-challenge.vesla-app.site` TXT records appear

### Possible Root Causes

- Digital Ocean API token invalid or lacks DNS write permissions
- DNS challenge timing out before TXT record propagates
- Certificate resolver name mismatch
- Let's Encrypt rate limiting
- Traefik can't write to Digital Ocean DNS
- Wrong DO_AUTH_TOKEN format in environment
- Email in traefik.yml might not be valid

### Success Criteria

When fixed, these should work:
```bash
# 1. HTTPS works without -k flag
curl -I https://test.vesla-app.site
# Should return: HTTP/2 200

# 2. Certificate is from Let's Encrypt
echo | openssl s_client -servername test.vesla-app.site \
  -connect SERVER_IP:443 2>/dev/null | \
  openssl x509 -noout -issuer
# Should show: issuer=C = US, O = Let's Encrypt, CN = R3 (or similar)

# 3. acme.json has certificate data
cat /opt/vesla/traefik/letsencrypt/acme.json | jq .
# Should have nested JSON with certificates, not {}
```

---

## Minor Issue 1: Docker Compose Warning

### The Problem

```
WARN[0000] The "vaRQX5hyIB0yoG" variable is not set. Defaulting to a blank string.
```

Appears 4-5 times when running `docker compose up` or `docker compose logs`.

### What's Been Tried

1. ✅ Escaped `$` as `$$` in `.env` file (required for bcrypt hash)
2. ✅ Removed dashboard labels from `docker-compose.yml`
3. ✅ Moved dashboard config to `config/dashboard.yml`
4. ❌ Warning still persists

### Next Steps to Fix

1. **Check if config/dashboard.yml has variable reference**:
   ```bash
   cat /opt/vesla/traefik/config/dashboard.yml
   # Look for: ${TRAEFIK_DASHBOARD_PASSWORD_HASH}
   # Should have hardcoded hash instead
   ```

2. **Run docker compose config to see resolved config**:
   ```bash
   cd /opt/vesla/traefik
   docker compose config
   # Look for where the variable appears
   ```

3. **Grep for the string in all files**:
   ```bash
   cd /opt/vesla/traefik
   grep -r "vaRQX5hyIB0yoG" .
   # Find which file has the reference
   ```

4. **Check for multiple docker-compose files**:
   ```bash
   cd /opt/vesla/traefik
   ls -la docker-compose*.yml
   ```

### Why It Matters

It's a minor annoyance but suggests a configuration issue. Won't block deployment but should be fixed for cleanliness.

---

## Minor Issue 2: Incomplete Firewall Rules

### The Problem

Two firewall rules missing:

1. **ICMP (ping) rule failed** during initial setup:
   ```
   ERROR: Unsupported protocol 'icmp'
   ```

2. **No port needed for Vesla API** - API will be behind Traefik

### Current Firewall State

```bash
$ sudo ufw status verbose
22/tcp    ALLOW IN    YOUR_IP_ADDRESS
22/tcp    ALLOW IN    100.64.0.0/10  # Tailscale
22/tcp    LIMIT IN    Anywhere
80/tcp    ALLOW IN    Anywhere
443/tcp   ALLOW IN    Anywhere
# Missing: ICMP rule
```

### Next Steps to Fix

```bash
# Add ICMP rule (fixed syntax)
sudo ufw allow from YOUR_IP_ADDRESS proto icmp comment 'ICMP from admin'
sudo ufw allow from 100.64.0.0/10 proto icmp comment 'ICMP from Tailscale'

# Verify
sudo ufw status numbered
```

**Note:** Vesla Server API will listen on `127.0.0.1:5001` (localhost only) and be accessed via Traefik proxy at `https://api.vesla-app.site`. No firewall port needed.

---

## Key File Locations

### Configuration Files

```
/opt/vesla/traefik/
├── .env                          # DO token, password hash
├── traefik.yml                   # Static config (CRITICAL)
├── docker-compose.yml            # Traefik container
├── config/
│   └── dashboard.yml             # Dashboard routing
└── letsencrypt/
    └── acme.json                 # Certificate storage (600 perms)
```

### Scripts

```
/opt/vesla/tools/
└── manage-dns.py                 # DNS A record management
```

### Future (not built yet)

```
/opt/vesla/server/
├── api.py                        # Flask API (POST /api/deploy)
├── builder.py                    # Docker build logic
├── deployer.py                   # Container deployment
└── config.yaml                   # Server settings
```

---

## Quick Commands Reference

### Check Traefik Status

```bash
cd /opt/vesla/traefik

# View logs
docker compose logs -f traefik

# Check for errors
docker compose logs traefik | grep -i error

# Restart
docker compose restart

# View loaded config
docker exec traefik cat /etc/traefik/traefik.yml
```

### Test Certificates

```bash
# Check HTTPS (should work without -k)
curl -I https://test.vesla-app.site

# View certificate issuer
echo | openssl s_client -servername test.vesla-app.site \
  -connect SERVER_IP:443 2>/dev/null | \
  openssl x509 -noout -issuer -dates

# Check acme.json content
cat /opt/vesla/traefik/letsencrypt/acme.json | jq .
```

### Test DNS

```bash
# Check resolution
dig @8.8.8.8 test.vesla-app.site +short

# List all A records
cd /opt/vesla/tools
./manage-dns.py list vesla-app.site
```

### Test Digital Ocean API

```bash
source /opt/vesla/traefik/.env

# Test token
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account

# Test domains access
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/domains
```

---

## Architecture Overview

```
Developer → vesla push (CLI)
    ↓
Vesla Server API (Flask on :5001)
    ↓
Docker Build + Deploy
    ↓
Traefik (reverse proxy)
    ↓ registers container
    ↓ creates DNS via Digital Ocean API
    ↓ gets Let's Encrypt cert via DNS-01 challenge
    ↓
HTTPS app at subdomain.domain.com
```

### Current State

- ✅ Traefik running and accessible
- ✅ DNS API working (manage-dns.py)
- ✅ Docker working
- ❌ **Let's Encrypt certificates not working** ← FIX THIS FIRST
- ⏳ Vesla Server API not built yet (next milestone)

---

## Important Gotchas

1. **Bcrypt hashes:** `$` must be escaped as `$$` in `.env` and YAML files
2. **File provider:** Doesn't expand environment variables - hardcode values
3. **Certificate resolver name:** Must match in traefik.yml and labels
4. **DNS propagation:** Wait 1-2 minutes after creating A record
5. **acme.json permissions:** Must be 600, owned by 1000:999
6. **Let's Encrypt rate limits:** 50 certs/week - use staging for testing
7. **Traefik dashboard:** Use file provider OR labels, not both

---

## What Worked So Far

### Server Hardening
- ✅ SSH key authentication configured
- ✅ Firewall mostly configured (UFW)
- ✅ Tailscale VPN installed
- ✅ Docker installed, user in docker group

### Traefik Setup
- ✅ Container starts successfully
- ✅ Docker socket accessible (user 1000:999)
- ✅ Configuration loads from traefik.yml
- ✅ Dashboard accessible via Tailscale
- ✅ No permission errors on logs or acme.json

### DNS Configuration
- ✅ 4 domains pointed to server IP
- ✅ manage-dns.py script working
- ✅ Test subdomain (test.vesla-app.site) has A record
- ✅ DNS propagation verified with dig

### Configuration
- ✅ Bcrypt password hash properly escaped
- ✅ Dashboard config moved to file provider
- ✅ Docker Compose labels removed from dashboard
- ✅ Network created (vesla-network)

---

## What Didn't Work

### Certificate Acquisition
- ❌ Let's Encrypt certificates not being issued
- ❌ Traefik serving self-signed certs instead
- ❌ Unknown why DNS-01 challenge failing
- ❌ Need debug logs to diagnose

### Minor Issues
- ❌ Docker Compose variable warning persists
- ❌ ICMP firewall rule not applied
- ❌ Haven't verified DO API token works

---

## Next Agent Action Plan

**Priority 1: Fix Certificates (CRITICAL)**

1. Enable DEBUG logging in traefik.yml
2. Restart Traefik and watch logs
3. Verify DO API token with curl
4. Check acme.json content
5. Look for ACME challenge errors in logs
6. Verify certificate resolver name consistency
7. Check for rate limiting at crt.sh
8. If needed, switch to staging Let's Encrypt

**Priority 2: Clean Up Warnings**

1. Find source of Docker Compose variable warning
2. Fix config/dashboard.yml if it has ${VAR} syntax
3. Verify with `docker compose config`

**Priority 3: Complete Firewall**

1. Add ICMP rules for admin IP and Tailscale
2. Verify no other ports needed

**Priority 4: Build Vesla Server API**

Once certificates work, build the Flask API that receives deployments.

---

## Resources

- **CLAUDE.md:** Full project documentation in `/opt/vesla/CLAUDE.md`
- **Traefik Docs:** https://doc.traefik.io/traefik/
- **Let's Encrypt DNS-01:** https://letsencrypt.org/docs/challenge-types/#dns-01-challenge
- **Digital Ocean API:** https://docs.digitalocean.com/reference/api/

---

## Environment Access

```bash
# SSH to server
ssh vesla@SERVER_IP  # Key auth only

# Or via Tailscale
ssh vesla@100.x.x.x

# Switch to project directory
cd /opt/vesla/traefik
```

### Credentials Location

- DO API token: `/opt/vesla/traefik/.env`
- Traefik dashboard password: `/opt/vesla/traefik/.env`

---

## Success Criteria for This Phase

**Phase 1 Complete When:**
- ✅ `curl -I https://test.vesla-app.site` works without `-k`
- ✅ Certificate issuer is Let's Encrypt (not self-signed)
- ✅ `acme.json` contains certificate data
- ✅ No Docker Compose warnings
- ✅ Firewall rules complete

**Then Move to Phase 2:**
- Build Vesla Server API (Flask)
- Build Vesla CLI client
- Test full deployment workflow

---

## Final Notes

The foundation is solid. Traefik is running, DNS works, everything is configured correctly **on paper**. The certificate issue is likely something simple like:
- Invalid/expired DO token
- DNS challenge timing out
- Rate limiting
- Typo in configuration

Start with debug logs - they will tell you exactly what's failing.

Good luck! 🚀
