# Vesla Server - Quick Start Guide

## What You Have Now

The complete Vesla server infrastructure is ready:

✅ **Traefik** - Reverse proxy with Let's Encrypt certificates
✅ **DNS Manager** - Automatic Digital Ocean DNS record creation
✅ **Image Builder** - Auto-detects runtime and builds Docker images
✅ **Container Deployer** - Deploys containers with Traefik labels
✅ **Flask API** - RESTful API for deployments

## Installation Steps

### 1. Install the Server

```bash
cd /opt/vesla/server
./setup.sh
```

This installs Python dependencies in a virtual environment.

### 2. Install the Systemd Service

```bash
sudo ./install-service.sh
```

### 3. Start the Service

```bash
sudo systemctl start vesla-server
sudo systemctl status vesla-server
```

### 4. Create DNS Record for API

The API needs a DNS record to be accessible. Run:

```bash
# From your local machine or via Tailscale
SERVER_IP="YOUR_SERVER_IP"
cd /opt/vesla/tools  # (if manage-dns.py exists)
# OR use Digital Ocean web interface to create:
# A record: api.vesla-app.site -> SERVER_IP
```

Or manually create an A record in Digital Ocean:
- Subdomain: `api`
- Domain: `vesla-app.site`
- IP: Your server IP

### 5. Restart Traefik to Pick Up API Config

```bash
cd /opt/vesla/traefik
docker compose restart
```

Wait 1-2 minutes for Let's Encrypt certificate.

### 6. Test the API

```bash
# Health check (no auth needed)
curl https://api.vesla-app.site/health

# Should return: {"status":"healthy","service":"vesla-server"}
```

## Your API Token

```
75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa
```

Use this token for all API requests:
```bash
Authorization: Bearer 75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa
```

## Test Deployment

Create a simple test app:

```bash
# 1. Create test directory
mkdir -p ~/test-app && cd ~/test-app

# 2. Create Flask app
cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Vesla!"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# 3. Create requirements
echo "flask==3.0.0" > requirements.txt

# 4. Create vesla.yaml
cat > vesla.yaml << 'EOF'
app: testapp
domain: testapp.vesla-app.site
env:
  PORT: 5000
EOF

# 5. Package code
tar -czf code.tar.gz app.py requirements.txt

# 6. Deploy!
curl -X POST https://api.vesla-app.site/api/deploy \
  -H "Authorization: Bearer 75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa" \
  -F "code=@code.tar.gz" \
  -F "config=$(cat vesla.yaml)"

# 7. Wait 1-2 minutes for DNS and certificate

# 8. Test!
curl https://testapp.vesla-app.site
```

## File Structure

```
/opt/vesla/server/
├── api.py              # Flask API (main entry point)
├── builder.py          # Docker image builder
├── deployer.py         # Container deployer
├── dns_manager.py      # DNS management
├── config.yaml         # Configuration
├── requirements.txt    # Python dependencies
├── setup.sh            # Setup script
├── install-service.sh  # Service installer
├── vesla-server.service # Systemd service file
├── README.md           # Full documentation
└── venv/               # Python virtual environment (created by setup.sh)

/opt/vesla/traefik/config/
├── dashboard.yml       # Traefik dashboard config
└── vesla-api.yml       # Routes traffic to Vesla API
```

## Monitoring

```bash
# View service logs
sudo journalctl -u vesla-server -f

# Check container status
docker ps

# Check Traefik logs
cd /opt/vesla/traefik
docker compose logs -f
```

## Common Issues

### "Connection refused" when testing API

- Check service is running: `sudo systemctl status vesla-server`
- Check it's listening: `netstat -tlnp | grep 5001`
- View logs: `sudo journalctl -u vesla-server -n 50`

### DNS not resolving

- Check A record exists in Digital Ocean
- Test DNS: `dig @8.8.8.8 api.vesla-app.site +short`
- Wait 1-2 minutes for propagation

### Certificate errors

- Check Traefik logs: `docker compose logs traefik | grep -i acme`
- Verify DO token works: `curl -H "Authorization: Bearer $DO_AUTH_TOKEN" https://api.digitalocean.com/v2/account`
- Check `acme.json` has content: `cat /opt/vesla/traefik/letsencrypt/acme.json | jq .`

## Next Steps

1. **Build the CLI client** - Create `vesla` CLI tool for easy deployments
2. **Test with different runtimes** - Python, Node.js, static sites
3. **Add database support** - Deploy PostgreSQL/MySQL containers
4. **Add app management** - List, restart, scale apps
5. **Set up monitoring** - Health checks and alerts

## Need Help?

See `/opt/vesla/server/README.md` for complete documentation.
