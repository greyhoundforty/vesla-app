# Certificate Issue - Troubleshooting Checklist

**Problem:** Traefik serving self-signed certificates instead of Let's Encrypt

**Goal:** Get valid Let's Encrypt certificates via DNS-01 challenge

---

## Quick Diagnostic Steps (Do These First)

### 1. Enable Debug Logging

```bash
cd /opt/vesla/traefik
nano traefik.yml
```

Change line:
```yaml
log:
  level: INFO  # ← Change this
```

To:
```yaml
log:
  level: DEBUG  # ← More verbose
```

Restart and watch:
```bash
docker compose restart
docker compose logs -f | tee /tmp/traefik-debug.log
```

**Look for:**
- "acme" errors
- "certificate" errors
- "digitalocean" errors
- "DNS challenge" failures

### 2. Verify DO API Token Works

```bash
cd /opt/vesla/traefik
source .env

# Test account access
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account

# Test domains access
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/domains
```

**Expected:** JSON response with account/domain info
**If 401 Unauthorized:** Token is invalid - regenerate in Digital Ocean dashboard

### 3. Check acme.json Content

```bash
cat /opt/vesla/traefik/letsencrypt/acme.json
```

**Expected:** JSON structure with certificates
```json
{
  "digitalocean": {
    "Account": {...},
    "Certificates": [...]
  }
}
```

**If empty `{}`:** Traefik hasn't successfully obtained any certificates yet

### 4. Check Certificate Resolver Name

```bash
# In traefik.yml
cd /opt/vesla/traefik
grep -A 5 "certificatesResolvers:" traefik.yml
# Should show: digitalocean:

# In container labels (when you deploy an app)
# Should have: traefik.http.routers.NAME.tls.certresolver=digitalocean
```

**Must match exactly** (case-sensitive)

### 5. Check for Rate Limiting

Visit: https://crt.sh/?q=vesla-app.site

**If many certificates issued:** You hit Let's Encrypt rate limit (50/week)

**Solution:** Use staging server temporarily:
```yaml
# In traefik.yml under certificatesResolvers.digitalocean.acme:
caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"
```

### 6. Verify Email in traefik.yml

```bash
grep "email:" /opt/vesla/traefik/traefik.yml
```

**Must be a valid email address** - Let's Encrypt requires this

---

## Common Issues and Fixes

### Issue: DO Token Invalid

**Symptom:** 401 errors when testing API
**Fix:**
1. Go to Digital Ocean dashboard → API → Tokens
2. Generate new token with "Read" and "Write" scopes
3. Update `/opt/vesla/traefik/.env`:
   ```bash
   DO_AUTH_TOKEN=dop_v1_NEW_TOKEN_HERE
   ```
4. Restart: `docker compose restart`

### Issue: DNS Challenge Timeout

**Symptom:** Logs show "timeout" or "DNS propagation"
**Fix:** Increase delay:
```yaml
# In traefik.yml
dnsChallenge:
  provider: digitalocean
  delayBeforeCheck: 30  # Wait 30 seconds for DNS propagation
```

### Issue: Wrong Environment Variable Name

**Symptom:** Logs show "missing credentials"
**Fix:** Traefik's Digital Ocean provider expects `DO_AUTH_TOKEN` (not `DIGITALOCEAN_TOKEN`)

Check docker-compose.yml:
```yaml
environment:
  - DO_AUTH_TOKEN=${DO_AUTH_TOKEN}  # Must be exactly this
```

### Issue: acme.json Permission Denied

**Symptom:** "permission denied" in logs
**Fix:**
```bash
cd /opt/vesla/traefik
sudo chown 1000:999 letsencrypt/acme.json
sudo chmod 600 letsencrypt/acme.json
```

### Issue: Port 443 Not Accessible

**Symptom:** Can't connect to HTTPS at all
**Fix:**
```bash
# Check Traefik is listening
docker compose ps

# Check firewall
sudo ufw status | grep 443

# Should show: 443/tcp ALLOW Anywhere
```

### Issue: Wildcard Domain Config Wrong

**Symptom:** Certs requested for each subdomain separately
**Fix:** In traefik.yml:
```yaml
entryPoints:
  websecure:
    address: ":443"
    http:
      tls:
        domains:
          - main: "vesla-app.site"
            sans:
              - "*.vesla-app.site"  # Wildcard for all subdomains
```

---

## Step-by-Step Fix Procedure

Follow these steps **in order**:

1. **Enable debug logging** (see section 1 above)
2. **Check DO token** (section 2) - if invalid, regenerate
3. **Restart Traefik** with new logging
4. **Watch logs** for specific error messages
5. **Check acme.json** - should start populating with attempts
6. **Wait 2-3 minutes** for DNS challenge to complete
7. **Test with curl**:
   ```bash
   curl -I https://test.vesla-app.site
   ```
8. **Verify certificate**:
   ```bash
   echo | openssl s_client -connect test.vesla-app.site:443 2>/dev/null | \
     openssl x509 -noout -issuer
   ```

---

## Log Patterns to Look For

### Good Signs

```
level=debug msg="Obtaining certificate..." domain=vesla-app.site
level=debug msg="Using DNS Challenge provider: digitalocean"
level=debug msg="Created TXT record: _acme-challenge.vesla-app.site"
level=info msg="Certificate obtained successfully" domains=[vesla-app.site *.vesla-app.site]
```

### Bad Signs

```
level=error msg="Unable to obtain certificate" error="invalid credentials"
→ DO token is wrong

level=error msg="DNS challenge failed" error="timeout"
→ DNS not propagating fast enough, increase delayBeforeCheck

level=error msg="rate limit exceeded"
→ Switch to staging Let's Encrypt server

level=error msg="permission denied" file="acme.json"
→ Fix file permissions
```

---

## Test Endpoints

Once you think it's fixed, test with these:

```bash
# Test 1: HTTPS works
curl -I https://test.vesla-app.site
# Should: Return HTTP/2 200 (not error)

# Test 2: Certificate is valid
curl https://test.vesla-app.site
# Should: NOT show "SSL certificate problem"

# Test 3: Certificate issuer
echo | openssl s_client -servername test.vesla-app.site \
  -connect YOUR_SERVER_IP:443 2>/dev/null | \
  openssl x509 -noout -text | grep Issuer
# Should: Show "Let's Encrypt" (or "Staging" if using staging server)

# Test 4: Certificate dates
echo | openssl s_client -servername test.vesla-app.site \
  -connect YOUR_SERVER_IP:443 2>/dev/null | \
  openssl x509 -noout -dates
# Should: Show valid dates (not expired)
```

---

## Files to Check/Edit

All relative to `/opt/vesla/traefik/`:

1. **`.env`** - DO_AUTH_TOKEN value
2. **`traefik.yml`** - Certificate resolver config, email, logging level
3. **`docker-compose.yml`** - Environment variable mapping
4. **`letsencrypt/acme.json`** - Certificate storage (check content)

---

## Nuclear Option (Start Fresh)

If nothing works, start over with certificates:

```bash
cd /opt/vesla/traefik

# Backup current config
cp letsencrypt/acme.json letsencrypt/acme.json.bak

# Clear certificate storage
echo '{}' | sudo tee letsencrypt/acme.json
sudo chmod 600 letsencrypt/acme.json
sudo chown 1000:999 letsencrypt/acme.json

# Enable staging (to avoid rate limits)
nano traefik.yml
# Add under certificatesResolvers.digitalocean.acme:
#   caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"

# Restart and watch
docker compose down
docker compose up -d
docker compose logs -f | grep -i acme
```

Wait 2-3 minutes. If staging certs work, switch back to production:
- Remove `caServer` line
- Clear acme.json again
- Restart

---

## Success Criteria

✅ `curl -I https://test.vesla-app.site` returns 200
✅ No "SSL certificate problem" error
✅ Certificate issuer is "Let's Encrypt"
✅ `acme.json` has certificate data
✅ Traefik logs show "Certificate obtained successfully"

When all above are true, certificates are working! 🎉

---

## Next Steps After Fix

1. Test with a real app deployment (not just Traefik dashboard)
2. Verify wildcard certs work for multiple subdomains
3. Move to building Vesla Server API
4. Fix minor issues (Docker warning, firewall)

---

## Need More Help?

Check these files:
- `/opt/vesla/.prompt-extraction/current-state-and-next-steps.md` - Full context
- `/opt/vesla/CLAUDE.md` - Complete project documentation
- Debug log: `/tmp/traefik-debug.log` - If you ran the command above

Good luck! The fix is probably simpler than you think. 🚀
