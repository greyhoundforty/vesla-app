# Vesla Test Application - Go

A simple Go HTTP application for testing Vesla deployments.

## Features

- Simple web interface showing deployment info
- Health check endpoint at `/health`
- JSON info endpoint at `/info`
- Reads PORT from environment variables
- Uses only Go standard library (no external dependencies)
- Shows runtime version, hostname, platform, and uptime

## Local Testing

```bash
# Run locally
go run main.go

# Or build and run
go build -o app
./app

# Visit http://localhost:8080
```

## Deployment with Vesla

```bash
# From your local machine with vesla CLI
vesla push

# The app will be deployed to https://example-go.vesla-app.site
```

## Endpoints

- `GET /` - HTML home page with deployment info
- `GET /health` - Health check (returns JSON with status and uptime)
- `GET /info` - JSON information about the app, runtime, and environment

## Configuration

See `vesla.yaml` for deployment configuration:
- Domain: example-go.vesla-app.site
- Runtime: Go (auto-detected from go.mod)
- Health check: /health
- Resources: 128MB RAM, 0.25 CPU cores
- Environment: Production-ready

## Dependencies

- Go 1.21 or higher
- No external dependencies (uses standard library only)

## Notes

Go applications benefit from multi-stage builds in Vesla, resulting in:
- Smaller final images (compiled binary only)
- Better security (no build tools in runtime)
- Faster deployments
