# Vesla

A Piku-inspired CLI deployment tool that automates application deployment with automatic HTTPS, DNS management, and Docker containerization.

## Overview

Vesla allows developers to deploy applications by simply pushing code to a server. The platform handles:

- **Automatic containerization**: Detects language/framework and builds appropriate Docker containers
- **HTTPS by default**: Integrates with Let's Encrypt for free SSL certificates via DNS-01 challenge
- **Reverse proxy**: Routes requests using Traefik 2.11 with automatic service discovery
- **DNS management**: Creates DNS A records automatically via Digital Ocean API
- **Multi-language support**: Python, Node.js, Go, Ruby, PHP, Java, Rust, .NET, and more

## Architecture

```
Developer Workstation          Vesla Server (Ubuntu)
    ↓                                  ↓
  vesla CLI ──HTTPS──→ Vesla API (Flask)
                            ├─ Builder (Docker)
                            ├─ Traefik (Reverse Proxy)
                            └─ DNS Manager (DigitalOcean)
                                  ↓
                         Docker Containers
                              ↓
                         Traefik Routes
                              ↓
                  subdomain.domain.com (HTTPS)
```

## Quick Start

### Prerequisites

- Vesla CLI installed locally (`~/.local/bin/vesla`)
- Access to Vesla server API
- DigitalOcean API token (for DNS management)
- Application code with appropriate config file

### Configuration

First, configure the CLI with your server details:

```bash
vesla config set server_url https://api.vesla-app.site
vesla config set api_token YOUR_API_TOKEN_HERE
```

Verify configuration:
```bash
vesla config list
```

### Initializing an Application

In your project directory:

```bash
# Generate vesla.yaml
vesla init

# Edit vesla.yaml with your app-specific config
nano vesla.yaml
```

### Deploying

```bash
# Deploy from your project directory
vesla push

# Check deployment status
vesla status myapp

# View logs
vesla logs myapp --tail 50
```

## Application Configuration

Each application is configured via `vesla.yaml`:

```yaml
app: myapp                          # Application name
domain: myapp.vesla-app.site        # Domain name
runtime: python                     # Language/runtime
env:                               # Environment variables
  PORT: 5000
  DEBUG: false
health_check: /health              # Health check endpoint
resources:                         # Resource limits
  memory: 256M
  cpus: 0.25
```

### Supported Runtimes

- **Python**: Flask, Django, FastAPI (requires `requirements.txt`)
- **Node.js**: Express, NestJS, Next.js (requires `package.json`)
- **Go**: net/http, Gin, Echo, Fiber (requires `go.mod` and `main.go`)
- **Ruby**: Rails, Sinatra (requires `Gemfile`)
- **PHP**: Laravel, Symfony (requires `composer.json`)
- **Java**: Spring Boot, Gradle, Maven (auto-detected)
- **Rust**: Actix, Rocket, Axum (requires `Cargo.toml`)
- **.NET**: ASP.NET Core (requires `*.csproj`)
- **Static**: HTML/CSS/JS sites (requires `index.html`)

### Custom Dockerfile

For advanced use cases, provide your own `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## Example Applications

Three example applications are provided to demonstrate Vesla deployment:

### Python Example
```bash
cd example-apps/python
# Requires: Flask framework
pip install -r requirements.txt
python app.py  # Runs locally on port 5000
```

### Node.js Example
```bash
cd example-apps/node
# Requires: Express framework
npm install
npm start  # Runs locally on port 3000
```

### Go Example
```bash
cd example-apps/go
# Requires: Go 1.21+
go run main.go  # Runs locally on port 8080
```

All examples provide:
- `GET /` - HTML home page with deployment info
- `GET /health` - Health check endpoint
- `GET /info` - JSON metadata about the running app

## CLI Commands

### Deployment
```bash
vesla push                    # Deploy from current directory
vesla status <app>           # Show app status
vesla logs <app> [--tail N]  # View app logs
vesla delete <app>           # Delete app
```

### Management
```bash
vesla list                   # List all deployed apps
vesla config set <key> <value>  # Configure CLI
vesla config get <key>      # Show configuration value
```

### Initialization
```bash
vesla init                   # Create vesla.yaml for new app
vesla init --force           # Overwrite existing vesla.yaml
```

## Project Structure

```
vesla-app/
├── cli/                     # Vesla CLI tool
│   ├── vesla               # Main CLI script
│   ├── requirements.txt    # Python dependencies
│   └── README.md
├── server/                 # Vesla API server
│   ├── api.py             # Flask API endpoints
│   ├── builder.py         # Docker build orchestration
│   ├── deployer.py        # Container deployment logic
│   ├── dns_manager.py     # DigitalOcean DNS integration
│   ├── requirements.txt   # Python dependencies
│   └── BUILDPACKS.md      # Language detection details
├── dashboard/              # Web dashboard
│   ├── app.py             # Flask dashboard application
│   ├── templates/
│   └── requirements.txt
├── traefik/               # Reverse proxy configuration
│   ├── traefik.yml        # Static configuration
│   ├── docker-compose.yml # Container setup
│   └── config/
│       ├── dashboard.yml  # Dashboard routing
│       └── vesla-api.yml  # API routing
├── example-apps/          # Reference implementations
│   ├── python/
│   ├── node/
│   └── go/
└── tools/                 # Utility scripts
    └── create-api-dns.py  # DNS record creation
```

## Server Setup

### Requirements
- Ubuntu 24.04 or similar Linux distribution
- Docker and Docker Compose
- DigitalOcean account (for DNS management)
- Domain name(s) configured in DigitalOcean
- Public server IP address

### Installation
```bash
# SSH into server
ssh user@server-ip

# Clone repository
git clone <repo-url> /opt/vesla
cd /opt/vesla

# Setup Traefik
cd traefik
docker compose up -d

# Setup API server
cd ../server
docker compose up -d

# Setup dashboard (optional)
cd ../dashboard
docker compose up -d
```

### Configuration Files

Create `/opt/vesla/traefik/.env`:
```
DO_AUTH_TOKEN=your_digitalocean_token
TRAEFIK_DASHBOARD_PASSWORD_HASH=your_bcrypt_hash
```

Create `/opt/vesla/server/.env`:
```
FLASK_ENV=production
API_TOKEN=your_api_token
DO_AUTH_TOKEN=your_digitalocean_token
```

## Security Considerations

- All API communication requires HTTPS with valid certificates
- API endpoints require bearer token authentication
- Containers run as non-root user (uid 1000)
- Environment variables are isolated per container
- Traefik dashboard only accessible via Tailscale VPN
- SSH key authentication required (no password login)

## Troubleshooting

### Connection timeout when pushing
- Verify server is running: `docker ps` on server
- Check Traefik logs: `docker compose logs traefik`
- Verify DNS resolution: `host api.vesla-app.site`
- Check firewall allows port 443: `ufw status`

### Application not starting
- Review build logs: `vesla logs myapp`
- Verify health check endpoint exists
- Check resource limits aren't too restrictive
- Ensure PORT environment variable is set correctly

### Certificate issues
- Verify DigitalOcean token is valid
- Check DNS propagation: `dig @8.8.8.8 domain.com`
- Review ACME challenge logs: `docker compose logs traefik | grep acme`
- Ensure DNS records exist for all configured domains

## Development

### Building from source
```bash
# Install CLI dependencies
cd cli
pip install -r requirements.txt

# Install server dependencies
cd ../server
pip install -r requirements.txt

# Run locally (for development only)
python api.py
```

### Testing deployments locally
Each example app can be tested locally:
```bash
cd example-apps/python
python app.py

# In another terminal
curl http://localhost:5000
curl http://localhost:5000/health
curl http://localhost:5000/info
```

## License

MIT

## Support

For issues, questions, or contributions, see the project repository.

---

**Last Updated**: January 2026  
**Vesla Version**: 0.1.0
