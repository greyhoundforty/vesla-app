# Vesla Server

The Vesla Server is the backend API that handles application deployments. It receives code from the Vesla CLI, builds Docker images, deploys containers, and configures DNS and Traefik routing.

## Architecture

```
vesla push (CLI)
  ↓ HTTPS POST /api/deploy
Vesla Server API (Flask on port 5001)
  ↓
  ├─> Build Docker image (runtime detection)
  ├─> Create DNS A record (Digital Ocean)
  └─> Deploy container with Traefik labels
  ↓
App available at https://app.vesla-app.site
```

## Installation

### 1. Run Setup Script

```bash
cd /opt/vesla/server
./setup.sh
```

This will:
- Install system dependencies (python3-venv, python3-pip)
- Create a Python virtual environment
- Install all Python dependencies

### 2. Configure Settings

Edit `config.yaml` to customize:
- **allowed_domains**: Domains that can be used for deployments
- **api_token**: Token for API authentication (already generated)
- **digitalocean.api_token**: Digital Ocean API token for DNS management
- **build settings**: Build timeouts and resource limits

### 3. Install Systemd Service

```bash
cd /opt/vesla/server
sudo ./install-service.sh
```

### 4. Start the Service

```bash
sudo systemctl start vesla-server
sudo systemctl status vesla-server
```

### 5. View Logs

```bash
# Follow logs in real-time
sudo journalctl -u vesla-server -f

# View recent logs
sudo journalctl -u vesla-server -n 100
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status.

### Deploy Application

```bash
POST /api/deploy
Authorization: Bearer <API_TOKEN>
Content-Type: multipart/form-data

Fields:
  - code: tarball file (.tar.gz)
  - config: vesla.yaml content (text)
```

**Example vesla.yaml:**

```yaml
app: myapp
domain: myapp.vesla-app.site
runtime: python  # optional: python, node, static, dockerfile
env:
  PORT: 5000
  DEBUG: false
health_check: /health  # optional
resources:  # optional
  memory: 512M
  cpus: 0.5
```

**Success Response (200):**

```json
{
  "status": "success",
  "app": "myapp",
  "url": "https://myapp.vesla-app.site",
  "container_id": "abc123def456",
  "build_time": 45.2,
  "message": "Deployment successful"
}
```

**Error Response (400/500):**

```json
{
  "status": "error",
  "error": "Build failed: Could not detect runtime",
  "details": "..."
}
```

### Get App Status

```bash
GET /api/apps/<app_name>
Authorization: Bearer <API_TOKEN>
```

Returns container status, image info, and ports.

### Delete App

```bash
DELETE /api/apps/<app_name>
Authorization: Bearer <API_TOKEN>
```

Stops and removes the application container.

### Get App Logs

```bash
GET /api/apps/<app_name>/logs?tail=100
Authorization: Bearer <API_TOKEN>
```

Returns recent container logs.

## Deployment Workflow

### 1. Runtime Detection

The server automatically detects the application runtime:

- **Dockerfile**: If present, uses it directly
- **Python**: Detects `requirements.txt` or `pyproject.toml`
- **Node.js**: Detects `package.json`
- **Static**: Detects `index.html`

### 2. Docker Image Build

Generates a Dockerfile based on runtime (if not provided) and builds the image.

**Generated Python Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt* pyproject.toml* ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

**Generated Node.js Dockerfile:**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 5000
CMD ["npm", "start"]
```

**Generated Static Dockerfile:**
```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
```

### 3. DNS Record Creation

Creates an A record in Digital Ocean DNS:
- Subdomain: `myapp`
- Domain: `vesla-app.site`
- IP: Server's public IP

### 4. Container Deployment

Deploys container with Traefik labels:

```bash
docker run -d \
  --name myapp \
  --network vesla-network \
  --restart unless-stopped \
  -e PORT=5000 \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.myapp.rule=Host(\`myapp.vesla-app.site\`)" \
  --label "traefik.http.routers.myapp.entrypoints=websecure" \
  --label "traefik.http.routers.myapp.tls.certresolver=digitalocean" \
  --label "traefik.http.services.myapp.loadbalancer.server.port=5000" \
  myapp:latest
```

### 5. Traefik Routes Traffic

Traefik automatically:
- Detects the new container
- Requests Let's Encrypt certificate via DNS-01 challenge
- Routes HTTPS traffic to the container

## Modules

### dns_manager.py

Handles DNS record management via Digital Ocean API:
- `create_a_record()`: Create A record
- `update_a_record()`: Update existing record
- `delete_a_record()`: Delete record
- `verify_dns_propagation()`: Verify DNS resolves correctly

### builder.py

Handles Docker image building:
- `detect_runtime()`: Detect app runtime from files
- `generate_dockerfile()`: Generate Dockerfile for runtime
- `build_image()`: Build Docker image from tarball
- `cleanup_old_images()`: Remove dangling images

### deployer.py

Handles container deployment:
- `deploy_container()`: Deploy container with Traefik labels
- `get_container_status()`: Get container status
- `stop_container()`: Stop running container
- `remove_container()`: Remove container
- `get_container_logs()`: Get container logs

### api.py

Main Flask application:
- `/health`: Health check endpoint
- `/api/deploy`: Deploy application
- `/api/apps/<name>`: Get/delete app
- `/api/apps/<name>/logs`: Get logs

## Configuration

### config.yaml

```yaml
# Allowed domains for app deployment
allowed_domains:
  - "vesla-app.cloud"
  - "vesla-app.com"
  - "vesla-app.club"
  - "vesla-app.site"

# API authentication token
api_token: "75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa"

# Digital Ocean configuration
digitalocean:
  api_token: "dop_v1_xxxxx"

# Docker configuration
docker:
  network: "vesla-network"

# Build configuration
build:
  max_build_time: 600  # 10 minutes
  default_memory_limit: "512m"
  default_cpu_limit: "0.5"
```

## Troubleshooting

### Service won't start

```bash
# Check service status
sudo systemctl status vesla-server

# View detailed logs
sudo journalctl -u vesla-server -n 50 --no-pager
```

### Docker permission denied

Ensure `vesla` user is in the docker group:

```bash
sudo usermod -aG docker vesla
```

### DNS records not created

Test Digital Ocean API token:

```bash
source /opt/vesla/traefik/.env
curl -H "Authorization: Bearer $DO_AUTH_TOKEN" \
  https://api.digitalocean.com/v2/account
```

Should return account info, not "Unauthorized".

### Container won't start

Check container logs:

```bash
docker logs <app-name>
```

Common issues:
- Port conflicts
- Missing environment variables
- Application crashes on startup

### Traefik not routing traffic

Check container labels:

```bash
docker inspect <app-name> | grep -A 10 Labels
```

Verify:
- `traefik.enable=true`
- Router rule has correct domain
- Certificate resolver is "digitalocean"

## Security

### API Authentication

All API endpoints (except `/health`) require Bearer token authentication:

```bash
Authorization: Bearer <API_TOKEN>
```

The token is defined in `config.yaml` and should be kept secret.

### Firewall

The Vesla API listens on `127.0.0.1:5001` (localhost only) and is accessed via Traefik at `https://api.vesla-app.site`. This means:

- No UFW port opening needed for 5001
- API not directly accessible from internet
- All traffic goes through Traefik with HTTPS

### Container Isolation

Deployed containers:
- Run on isolated `vesla-network`
- Have resource limits (CPU, memory)
- Cannot access host filesystem
- Restart automatically on failure

## Testing

### Manual Test

```bash
# 1. Create test app
mkdir test-app
cd test-app

# 2. Create simple Flask app
cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Vesla!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# 3. Create requirements.txt
echo "flask==3.0.0" > requirements.txt

# 4. Create vesla.yaml
cat > vesla.yaml << 'EOF'
app: testapp
domain: testapp.vesla-app.site
runtime: python
env:
  PORT: 5000
EOF

# 5. Create tarball
tar -czf code.tar.gz app.py requirements.txt

# 6. Deploy
curl -X POST https://api.vesla-app.site/api/deploy \
  -H "Authorization: Bearer <YOUR_API_TOKEN>" \
  -F "code=@code.tar.gz" \
  -F "config=$(cat vesla.yaml)"

# 7. Wait for deployment (1-2 minutes for DNS + cert)

# 8. Test deployed app
curl https://testapp.vesla-app.site
```

## Next Steps

1. **Build Vesla CLI**: Create the client-side CLI tool that packages code and sends it to this API
2. **Add app management**: List, restart, scale deployed apps
3. **Add logging**: Centralized logging for deployed apps
4. **Add monitoring**: Health checks and alerts
5. **Add database support**: PostgreSQL, MySQL container deployment
6. **Add environment secrets**: Secure secret management

## License

MIT
