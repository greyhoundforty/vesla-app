# Vesla Server Installation - Configuration Guide

## Overview

The `install-server.sh` script supports three modes of configuration:

1. **Interactive Mode** (default) - Prompts you for all values
2. **Config File Mode** - Load configuration from JSON or YAML file
3. **Command-Line Flags** - Pass values as arguments

## Interactive Mode (Default)

Simply run the script without arguments:

```bash
sudo bash install-server.sh
```

The script will prompt you for:
- Domain names (comma-separated)
- DigitalOcean API token
- Email for Let's Encrypt
- Dashboard password
- Optional: Install Tailscale
- Optional: Install Portainer

## Config File Mode

### Using JSON Configuration

Create a JSON file with your configuration:

```json
{
  "domains": "example.com,www.example.com",
  "do_token": "dop_v1_your_token_here",
  "acme_email": "admin@example.com",
  "dashboard_password": "secure_password_here",
  "install_tailscale": false,
  "install_portainer": true
}
```

Then run:

```bash
sudo bash install-server.sh --config /path/to/config.json
```

### Using YAML Configuration

Create a YAML file with your configuration:

```yaml
domains: "example.com,www.example.com"
do_token: "dop_v1_your_token_here"
acme_email: "admin@example.com"
dashboard_password: "secure_password_here"
install_tailscale: false
install_portainer: true
```

Then run:

```bash
sudo bash install-server.sh --config /path/to/config.yaml
```

## Command-Line Flags

Pass individual configuration values as flags:

```bash
sudo bash install-server.sh \
  --domains example.com,www.example.com \
  --do-token dop_v1_your_token_here \
  --email admin@example.com \
  --password secure_password_here \
  --portainer
```

### Available Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--config FILE` | Load configuration from file | `--config config.json` |
| `--domains DOMAINS` | Comma-separated domain names | `--domains example.com,www.example.com` |
| `--do-token TOKEN` | DigitalOcean API token | `--do-token dop_v1_...` |
| `--email EMAIL` | Email for Let's Encrypt | `--email admin@example.com` |
| `--password PASSWORD` | Traefik dashboard password | `--password secure_password` |
| `--tailscale` | Enable Tailscale installation | (no value needed) |
| `--portainer` | Enable Portainer installation | (no value needed) |
| `--help` | Show help message | (no value needed) |

## Example Workflows

### Automated CI/CD Deployment

Use a config file for reproducible deployments:

```bash
# Copy example config
cp .env.example.json vesla-config.json

# Edit with your values
nano vesla-config.json

# Run installation
sudo bash install-server.sh --config vesla-config.json
```

### Quick Setup with Flags

```bash
sudo bash install-server.sh \
  --domains api.example.com,dashboard.example.com \
  --do-token dop_v1_abcdef123456 \
  --email ops@example.com \
  --password MySecurePassword123! \
  --portainer
```

### Mixed Configuration

Load base config file, then override with flags:

```bash
sudo bash install-server.sh \
  --config base-config.json \
  --password override_password
```

## Security Considerations

### For Config Files

1. **Protect sensitive data**: Use restrictive file permissions
   ```bash
   chmod 600 vesla-config.json
   ```

2. **Never commit to version control**: Add to `.gitignore`
   ```bash
   echo "vesla-config.json" >> .gitignore
   echo "*-config.json" >> .gitignore
   ```

3. **Use example files**: Keep `.env.example.json` and `.env.example.yaml` in version control for documentation

### For Command-Line Flags

⚠️ **Warning**: Passing passwords as command-line arguments may expose them in:
- Shell history
- Process listings
- Logs

**Better approach**: Use config files with restricted permissions, or use interactive mode.

## Configuration Reference

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `domains` | Domains for SSL certificates | `example.com,www.example.com` |
| `do_token` | DigitalOcean API token | `dop_v1_abc...` |
| `acme_email` | Email for certificate renewal | `admin@example.com` |
| `dashboard_password` | Traefik admin password | Any secure password |

### Optional Fields

| Field | Default | Values |
|-------|---------|--------|
| `install_tailscale` | `false` | `true` or `false` |
| `install_portainer` | `false` | `true` or `false` |

## Troubleshooting

### "Config file not found"

Ensure the path is correct and the file exists:
```bash
ls -la /path/to/config.json
```

### "Unsupported config file format"

Only `.json` and `.yaml`/`.yml` files are supported. Check your file extension.

### "Domains not provided"

When using flags or config files, ensure all required fields are present. Check with:
```bash
sudo bash install-server.sh --help
```

### Installation still prompting for values

When using `--config` or flags, prompts are skipped. If you're still seeing prompts, some required fields may be missing. Ensure all four required fields are present:
- `domains`
- `do_token`
- `acme_email`
- `dashboard_password`

## Examples

### Example 1: Complete JSON Config

```json
{
  "domains": "api.myapp.com,dashboard.myapp.com,admin.myapp.com",
  "do_token": "dop_v1_9a8b7c6d5e4f3g2h1i0j",
  "acme_email": "ops@myapp.com",
  "dashboard_password": "GeneratedSecurePassword123!@#",
  "install_tailscale": true,
  "install_portainer": true
}
```

### Example 2: Complete YAML Config

```yaml
domains: "api.myapp.com,dashboard.myapp.com"
do_token: "dop_v1_9a8b7c6d5e4f3g2h1i0j"
acme_email: "ops@myapp.com"
dashboard_password: "GeneratedSecurePassword123!@#"
install_tailscale: true
install_portainer: true
```

### Example 3: Minimal Command-Line

```bash
sudo bash install-server.sh \
  --domains api.example.com \
  --do-token dop_v1_token \
  --email admin@example.com \
  --password password123
```

## Next Steps

After installation with any configuration method:

1. Verify installation: `sudo cat /opt/vesla/install.log`
2. Check running containers: `docker ps`
3. Access dashboard: `http://localhost:8080` (via SSH tunnel)
4. Deploy an app: See [QUICKSTART.md](QUICKSTART.md)
