# Vesla Test Application - Node.js

A simple Node.js Express application for testing Vesla deployments.

## Features

- Simple web interface showing deployment info
- Health check endpoint at `/health`
- JSON info endpoint at `/info`
- Reads PORT and NODE_ENV from environment variables
- Shows runtime version, hostname, and uptime

## Local Testing

```bash
# Install dependencies
npm install

# Run locally
npm start

# Visit http://localhost:3000
```

## Deployment with Vesla

```bash
# From your local machine with vesla CLI
vesla push

# The app will be deployed to https://example-node.vesla-app.site
```

## Endpoints

- `GET /` - HTML home page with deployment info
- `GET /health` - Health check (returns JSON with status and uptime)
- `GET /info` - JSON information about the app, runtime, and environment

## Configuration

See `vesla.yaml` for deployment configuration:
- Domain: example-node.vesla-app.site
- Runtime: Node.js (auto-detected from package.json)
- Health check: /health
- Resources: 256MB RAM, 0.25 CPU cores
- Environment: Production mode

## Dependencies

- Express.js 4.x for HTTP server
- Node.js 18+ required
