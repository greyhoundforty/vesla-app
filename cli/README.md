# Vesla CLI

Command-line tool for deploying applications to your Vesla server.

## Installation

### On Your Local Machine

```bash
# Clone or download the CLI
cd /path/to/vesla/cli

# Install
./install.sh
```

This will:
- Install Python dependencies (pyyaml, requests)
- Copy `vesla` to `~/.local/bin/`

### Configure CLI

```bash
# Set server URL
vesla config set server_url https://api.vesla-app.site

# Set API token
vesla config set api_token 75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa

# Verify configuration
vesla config list
```

## Usage

### Initialize a Project

```bash
cd /path/to/your/app
vesla init
```

This creates a `vesla.yaml` file:

```yaml
app: myapp
domain: myapp.vesla-app.site
env:
  PORT: 5000
```

### Deploy Your App

```bash
vesla push
```

This will:
1. Package your code into a tarball
2. Upload to the Vesla server
3. Build a Docker image
4. Create DNS record
5. Deploy container with Traefik routing
6. Request Let's Encrypt certificate

Your app will be live at `https://myapp.vesla-app.site` in 1-2 minutes.

### Check App Status

```bash
vesla status myapp
```

Shows container status, image, and creation time.

### View Logs

```bash
vesla logs myapp

# Get last 50 lines
vesla logs myapp --tail 50
```

### Delete App

```bash
vesla delete myapp

# Skip confirmation
vesla delete myapp -y
```

## vesla.yaml Configuration

### Minimal Configuration

```yaml
app: myapp
domain: myapp.vesla-app.site
```

### Full Configuration

```yaml
app: myapp
domain: myapp.vesla-app.site

# Runtime (optional - auto-detected)
# Options: python, node, static, dockerfile
runtime: python

# Environment variables
env:
  PORT: 5000
  DEBUG: false
  DATABASE_URL: postgres://...

# Health check endpoint (optional)
health_check: /health

# Resource limits (optional)
resources:
  memory: 512M
  cpus: 0.5
```

## Supported Runtimes

### Python

Detected by: `requirements.txt` or `pyproject.toml`

```
myapp/
├── app.py
├── requirements.txt
└── vesla.yaml
```

### Node.js

Detected by: `package.json`

```
myapp/
├── server.js
├── package.json
└── vesla.yaml
```

### Static Site

Detected by: `index.html`

```
myapp/
├── index.html
├── styles.css
└── vesla.yaml
```

### Custom Dockerfile

If `Dockerfile` exists, it will be used directly:

```
myapp/
├── Dockerfile
├── app.py
└── vesla.yaml
```

## Examples

### Python Flask App

```bash
mkdir myflaskapp && cd myflaskapp

# Create Flask app
cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Vesla!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# Create requirements.txt
echo "flask==3.0.0" > requirements.txt

# Initialize and deploy
vesla init
vesla push
```

### Node.js Express App

```bash
mkdir myexpressapp && cd myexpressapp

# Create Express app
cat > server.js << 'EOF'
const express = require('express');
const app = express();
const PORT = process.env.PORT || 5000;

app.get('/', (req, res) => {
    res.send('Hello from Vesla!');
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
EOF

# Create package.json
cat > package.json << 'EOF'
{
  "name": "myexpressapp",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
EOF

# Initialize and deploy
vesla init
vesla push
```

### Static Website

```bash
mkdir mysite && cd mysite

# Create HTML
cat > index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>My Site</title>
</head>
<body>
    <h1>Hello from Vesla!</h1>
</body>
</html>
EOF

# Initialize and deploy
vesla init
vesla push
```

## Workflow

```
Developer Machine              Vesla Server
───────────────                ────────────

vesla push
  │
  ├─ Package code
  │  └─ Creates tarball
  │
  ├─ Upload via HTTPS ────────> /api/deploy
  │                              │
  │                              ├─ Extract code
  │                              ├─ Detect runtime
  │                              ├─ Build Docker image
  │                              ├─ Create DNS record
  │                              ├─ Deploy container
  │                              └─ Return URL
  │
  └─ App live at URL <────────
     https://myapp.vesla-app.site
```

## Files Excluded from Upload

The following files are automatically excluded:

- `.git/`
- `__pycache__/`
- `*.pyc`
- `node_modules/`
- `.env`
- `venv/`

## Configuration File

CLI configuration is stored in `~/.vesla/config.yaml`:

```yaml
server_url: https://api.vesla-app.site
api_token: 75381b39010b8569286f46c5619ca00155f2f0c1a6cc08e09b8ab9c09f8699aa
```

## Troubleshooting

### "Cannot connect to server"

Check server health:

```bash
curl https://api.vesla-app.site/health
```

Should return: `{"status":"healthy","service":"vesla-server"}`

### "Authentication failed"

Verify your API token:

```bash
vesla config get api_token
```

Update if needed:

```bash
vesla config set api_token YOUR_CORRECT_TOKEN
```

### "Build failed"

Check if runtime can be detected:

- Python: Needs `requirements.txt` or `pyproject.toml`
- Node: Needs `package.json`
- Static: Needs `index.html`
- Or provide a `Dockerfile`

### "Domain not allowed"

The domain must use one of the allowed base domains:

- vesla-app.cloud
- vesla-app.com
- vesla-app.club
- vesla-app.site

Update `domain` in `vesla.yaml`:

```yaml
domain: myapp.vesla-app.site  # ✓ Valid
domain: myapp.example.com     # ✗ Not allowed
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `vesla init` | Initialize vesla.yaml in current directory |
| `vesla push` | Deploy current directory to server |
| `vesla status <app>` | Get status of deployed app |
| `vesla logs <app>` | View logs from deployed app |
| `vesla delete <app>` | Delete deployed app |
| `vesla config set <key> <value>` | Set configuration value |
| `vesla config get <key>` | Get configuration value |
| `vesla config list` | List all configuration |
| `vesla --version` | Show CLI version |

## Next Steps

1. **Install the CLI** on your local development machine
2. **Configure** with server URL and API token
3. **Create a test app** and deploy with `vesla push`
4. **Monitor** with `vesla status` and `vesla logs`
5. **Deploy real apps** from your projects

## License

MIT
