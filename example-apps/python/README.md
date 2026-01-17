# Vesla Test Application

A simple Python Flask application for testing Vesla deployments.

## Features

- Simple web interface showing deployment info
- Health check endpoint at `/health`
- JSON info endpoint at `/info`
- Reads PORT and DEBUG from environment variables

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Visit http://localhost:5000
```

## Deployment with Vesla

```bash
# From your local machine with vesla CLI
vesla push

# The app will be deployed to https://example.vesla-app.site
```

## Endpoints

- `GET /` - HTML home page with deployment info
- `GET /health` - Health check (returns JSON with status)
- `GET /info` - JSON information about the app and environment

## Configuration

See `vesla.yaml` for deployment configuration:
- Domain: example.vesla-app.site
- Runtime: Python (auto-detected from requirements.txt)
- Health check: /health
- Resources: 256MB RAM, 0.25 CPU cores
