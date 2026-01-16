# UFW Firewall Status for Vesla Dashboard

## Summary

**No UFW changes are required** for the Tailscale-based dashboard setup.

## Why No UFW Changes?

The dashboard is configured to be completely isolated from the public internet:

1. **Localhost Binding**: The dashboard container binds to `127.0.0.1:5002`
   - This port is NOT accessible from external networks
   - UFW doesn't need to block it because it's already unreachable

2. **Tailscale Layer**: Tailscale operates at the network layer (WireGuard VPN)
   - Encrypted tunnel between your devices
   - Doesn't use standard ports that UFW manages
   - Traffic goes through the Tailscale interface, not eth0

3. **No Public Ports**: Dashboard uses no publicly exposed ports
   - Not using port 80 (HTTP)
   - Not using port 443 (HTTPS)
   - Not using any custom ports accessible externally

## Current UFW Configuration

To verify your current UFW rules, run:

```bash
sudo ufw status verbose
```

Expected output:

```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    YOUR_IP_ADDRESS
22/tcp                     ALLOW IN    100.64.0.0/10       # Tailscale network
22/tcp                     LIMIT IN    Anywhere
80/tcp                     ALLOW IN    Anywhere            # Traefik HTTP
443/tcp                    ALLOW IN    Anywhere            # Traefik HTTPS
22/tcp (v6)                LIMIT IN    Anywhere (v6)
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)                ALLOW IN    Anywhere (v6)
```

**Notice:**
- ✓ Port 5002 (dashboard) is NOT listed - this is correct!
- ✓ Only ports 22, 80, 443 are exposed
- ✓ Dashboard is completely protected

## Port Mapping Overview

```
Public Internet
  ↓
  ├─ Port 80  → Traefik (deployed apps)
  ├─ Port 443 → Traefik (deployed apps)
  └─ Port 22  → SSH

Tailscale Network (100.64.0.0/10)
  ↓ WireGuard tunnel (encrypted)
  └─ Tailscale Serve → 127.0.0.1:5002 (dashboard)

Blocked/Unreachable from outside:
  ✗ Port 5002 (dashboard) - localhost only
  ✗ Port 5001 (API server) - localhost only
```

## Testing Security

### 1. Verify Dashboard is NOT Publicly Accessible

From a machine NOT on your Tailscale network:

```bash
# This should FAIL (connection refused/timeout)
curl http://your-server-ip:5002
curl https://your-server-ip:5002

# This should also FAIL (no DNS record)
curl https://dashboard.vesla-app.site
```

### 2. Verify Dashboard IS Accessible via Tailscale

From a device ON your Tailscale network:

```bash
# This should WORK
curl https://srv1.tail84fc1.ts.net/health

# Or open in browser
# https://srv1.tail84fc1.ts.net
```

### 3. Verify Localhost Access (on the server)

```bash
# This should WORK (localhost only)
curl http://localhost:5002/health

# This should FAIL (not bound to public IP)
curl http://$(hostname -I | awk '{print $1}'):5002/health
```

## Tailscale and UFW Interaction

Tailscale creates its own network interface (`tailscale0`) that UFW doesn't interfere with:

```bash
# View network interfaces
ip addr show tailscale0

# View Tailscale routes
ip route show | grep tailscale
```

Tailscale traffic:
- Uses UDP port 41641 for initial handshake (handled by Tailscale, not UFW)
- Establishes direct peer-to-peer connections when possible
- Falls back to relay servers if needed
- All traffic is encrypted with WireGuard

**UFW does not need to allow Tailscale ports** because:
1. Tailscale operates at a lower network layer
2. Outbound connections are allowed by default in UFW
3. Inbound Tailscale traffic uses established connections

## Security Best Practices

### What We're Doing Right

✓ **Principle of Least Privilege**: Only expose what's necessary
✓ **Defense in Depth**: Multiple layers (UFW + localhost bind + Tailscale auth)
✓ **Zero Trust**: Dashboard not accessible even with server IP
✓ **Encrypted Transport**: All Tailscale traffic uses WireGuard encryption

### Additional Recommendations

1. **Regularly review UFW rules**:
   ```bash
   sudo ufw status numbered
   ```

2. **Monitor Tailscale access**:
   ```bash
   tailscale status
   tailscale serve status
   ```

3. **Check for unauthorized listening ports**:
   ```bash
   sudo ss -tulpn | grep LISTEN
   ```

4. **Review Docker port bindings**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   ```

## If You Need to Change UFW

**You don't!** But if you want to add extra security:

### Option: Explicitly Block Port 5002 (Redundant but Harmless)

```bash
# This is unnecessary but won't hurt
sudo ufw deny 5002
```

### Option: Log Attempted Connections to Dashboard Port

```bash
# Log but don't block (for monitoring)
sudo ufw logging on
```

## Common Questions

### Q: Do I need to allow port 5002 in UFW?
**A:** No! Port 5002 is bound to localhost (127.0.0.1) and is not accessible externally.

### Q: Do I need to allow Tailscale ports in UFW?
**A:** No! Tailscale handles its own networking and doesn't require UFW rules.

### Q: What if I want to access the dashboard without Tailscale?
**A:** You can SSH tunnel:
```bash
ssh -L 5002:localhost:5002 vesla@your-server-ip
# Then visit http://localhost:5002 in your browser
```

### Q: Is the dashboard secure?
**A:** Yes! It's only accessible:
- From localhost (127.0.0.1)
- Via Tailscale (encrypted WireGuard VPN with authentication)

### Q: Can someone scan my server and find the dashboard?
**A:** No! Port scanning from the internet won't reveal port 5002 because:
- It's bound to localhost only
- Not exposed through any public interface
- No DNS record pointing to it

## Verification Checklist

Run these commands to verify security:

```bash
# 1. Check UFW status
sudo ufw status verbose

# 2. Verify dashboard binds to localhost only
docker ps | grep vesla-dashboard
# Should show: 127.0.0.1:5002->5002/tcp

# 3. Check listening ports
sudo ss -tulpn | grep :5002
# Should show: 127.0.0.1:5002 (not 0.0.0.0:5002)

# 4. Verify Tailscale Serve configuration
tailscale serve status
# Should show: proxy http://127.0.0.1:5002

# 5. Test external access (should FAIL)
curl -m 5 http://$(curl -s ifconfig.me):5002 2>&1
# Should timeout or connection refused
```

## Summary

✅ **No UFW changes needed**
✅ **Dashboard is localhost-only**
✅ **Tailscale Serve provides secure access**
✅ **Public internet cannot reach dashboard**
✅ **Current UFW rules are optimal**

The dashboard is properly secured and requires zero firewall modifications!
