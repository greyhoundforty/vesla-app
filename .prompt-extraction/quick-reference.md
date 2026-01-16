# Vesla - Quick Reference Card

**Project:** Deployment tool (push apps → auto HTTPS)
**Current Issue:** Certificates not working (self-signed instead of Let's Encrypt)

---

## Essential Commands

### Traefik Management
```bash
cd /opt/vesla/traefik

# View logs
docker compose logs -f traefik

# Restart
docker compose restart

# Stop/Start
docker compose down && docker compose up -d

# Check status
docker compose ps
```

### Certificate Debugging
```bash
# Enable debug logging
cd /opt/vesla/traefik
nano traefik.yml  # Change level: INFO → DEBUG
docker compose restart

# Watch for errors
docker compose logs -f | grep -E "acme|cert|error"

# Check cert storage
cat letsencrypt/acme.json | jq .

# Test HTTPS
curl -I https://test.vesla-app.site

# Check cert issuer
echo | openssl s_client -connect test.vesla-app.site:443 2>/dev/null | \
  openssl x509 -noout -issuer
```

### Digital Ocean API
```bash
cd /opt/vesla/traefik
source .env

# Test token
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account
```

### DNS Management
```bash
cd /opt/vesla/tools

# Create A record
./manage-dns.py create subdomain vesla-app.site SERVER_IP

# List records
./manage-dns.py list vesla-app.site

# Check DNS
dig @8.8.8.8 test.vesla-app.site +short
```

---

## Key File Locations

```
/opt/vesla/
├── traefik/
│   ├── .env                      ← DO token, password hash
│   ├── traefik.yml               ← Main config (CRITICAL)
│   ├── docker-compose.yml        ← Container definition
│   ├── config/dashboard.yml      ← Dashboard routing
│   └── letsencrypt/acme.json     ← Certificates (600 perms)
│
├── tools/
│   └── manage-dns.py             ← DNS A record script
│
├── CLAUDE.md                      ← Full project docs
└── .prompt-extraction/            ← You are here
    ├── current-state-and-next-steps.md
    ├── certificate-fix-checklist.md
    └── quick-reference.md
```

---

## Configuration Checklist

### traefik.yml
- [ ] `log.level: DEBUG` (for troubleshooting)
- [ ] `certificatesResolvers.digitalocean.acme.email` is valid
- [ ] `certificatesResolvers.digitalocean.acme.storage: "/letsencrypt/acme.json"`
- [ ] `dnsChallenge.provider: digitalocean`
- [ ] `entryPoints.websecure.http.tls.domains` has wildcard entries

### .env
- [ ] `DO_AUTH_TOKEN=dop_v1_...` (valid token)
- [ ] `TRAEFIK_DASHBOARD_PASSWORD_HASH=admin:$$2y$$05$$...` (escaped)

### docker-compose.yml
- [ ] `environment: - DO_AUTH_TOKEN=${DO_AUTH_TOKEN}`
- [ ] `user: "1000:999"` (correct docker group)
- [ ] Volumes mounted correctly

### letsencrypt/acme.json
- [ ] Permissions: 600
- [ ] Owner: 1000:999
- [ ] Content: Should have JSON (not empty `{}`)

---

## Common Issues Quick Fix

| Issue | Quick Fix |
|-------|-----------|
| Self-signed certs | Enable DEBUG logs, check DO token |
| DO token 401 | Regenerate token in DO dashboard |
| acme.json empty | Check logs for ACME errors |
| DNS timeout | Increase `delayBeforeCheck: 30` |
| Rate limit | Use staging: `caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"` |
| Permission denied | `chmod 600 acme.json && chown 1000:999 acme.json` |

---

## Test Sequence

1. Enable debug logs
2. Verify DO token works
3. Restart Traefik
4. Watch logs for 2-3 minutes
5. Test: `curl -I https://test.vesla-app.site`
6. Check issuer: `openssl s_client ... | grep Issuer`
7. Verify acme.json has content

---

## Domains Configured

- vesla-app.site
- vesla-dev.site
- vesla-staging.site
- vesla-prod.site

All pointed to server IP via Digital Ocean DNS.

---

## Architecture

```
vesla CLI → Vesla API → Docker Build → Traefik → HTTPS
                    ↓
             DNS (Digital Ocean)
                    ↓
             Let's Encrypt (DNS-01)
```

---

## Success Metrics

✅ Traefik running
✅ DNS configured
✅ Docker working
❌ **Certificates (FIX THIS FIRST)**
⏳ Vesla API (next)

---

## Resources

- Full docs: `/opt/vesla/CLAUDE.md`
- Troubleshooting: `/opt/vesla/.prompt-extraction/certificate-fix-checklist.md`
- Context: `/opt/vesla/.prompt-extraction/current-state-and-next-steps.md`
- Traefik docs: https://doc.traefik.io/traefik/
- Let's Encrypt: https://letsencrypt.org/docs/

---

**Start with certificates. Everything else depends on this working.**
