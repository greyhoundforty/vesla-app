# Installation Configuration Update

## Summary

Enhanced `install-server.sh` with flexible configuration options to support automated deployments and different use cases.

## New Features

### 1. Config File Support

Load all configuration from a single file:

```bash
sudo bash install-server.sh --config config.json
```

Supports both JSON and YAML formats:

**JSON Example:**
```json
{
  "domains": "example.com,www.example.com",
  "do_token": "dop_v1_...",
  "acme_email": "admin@example.com",
  "dashboard_password": "secure_password",
  "install_tailscale": false,
  "install_portainer": true
}
```

**YAML Example:**
```yaml
domains: "example.com,www.example.com"
do_token: "dop_v1_..."
acme_email: "admin@example.com"
dashboard_password: "secure_password"
install_tailscale: false
install_portainer: true
```

### 2. Command-Line Flags

Pass configuration values directly:

```bash
sudo bash install-server.sh \
  --domains example.com,www.example.com \
  --do-token dop_v1_... \
  --email admin@example.com \
  --password secure_password \
  --portainer \
  --tailscale
```

### 3. Interactive Mode (Default)

Still supports the original interactive prompts:

```bash
sudo bash install-server.sh
```

## Configuration Options

| Option | Flag | Config Key | Required |
|--------|------|-----------|----------|
| Domains | `--domains` | `domains` | Yes |
| DO Token | `--do-token` | `do_token` | Yes |
| Email | `--email` | `acme_email` | Yes |
| Password | `--password` | `dashboard_password` | Yes |
| Tailscale | `--tailscale` | `install_tailscale` | No |
| Portainer | `--portainer` | `install_portainer` | No |

## Files Created

1. **`.env.example.json`** - JSON configuration template
2. **`.env.example.yaml`** - YAML configuration template
3. **`INSTALL-CONFIG.md`** - Complete configuration guide with examples and security recommendations

## Implementation Details

### New Functions Added

- `parse_arguments()` - Parses command-line flags
- `load_config_file()` - Loads JSON/YAML configuration
- `show_usage()` - Displays help information

### Modified Functions

- `prompt_configuration()` - Now skips prompts if config is provided via flags/file
- `main()` - Now parses arguments before other initialization

### Features

- ✓ JSON configuration support (with fallback grep parser if jq unavailable)
- ✓ YAML configuration support
- ✓ Command-line flag support
- ✓ Full validation of required fields
- ✓ Helpful error messages
- ✓ Comprehensive help with `--help` flag

## Usage Examples

### Example 1: Config File (Recommended for automation)

```bash
# Copy example
cp .env.example.json vesla-config.json

# Edit with your values
nano vesla-config.json

# Protect it
chmod 600 vesla-config.json

# Run installation
sudo bash install-server.sh --config vesla-config.json
```

### Example 2: Command-Line Flags

```bash
sudo bash install-server.sh \
  --domains api.example.com \
  --do-token dop_v1_abcdef \
  --email ops@example.com \
  --password MyPassword123! \
  --portainer
```

### Example 3: Interactive (Default)

```bash
sudo bash install-server.sh
# Prompts for all values
```

## Security Notes

1. **Config Files**: Use `chmod 600` to protect files with sensitive data
2. **Version Control**: Add config files to `.gitignore`
3. **Example Files**: Keep `.env.example.*` files in the repo for documentation
4. **Command-Line**: Avoid passing sensitive data in flags when possible (shell history exposure)

## Help Command

```bash
sudo bash install-server.sh --help
```

## Testing

The script validates:
- Config file exists before loading
- All required fields are provided
- File format is supported (.json, .yaml)
- Configuration values are non-empty before proceeding

## Backward Compatibility

✓ Fully backward compatible - existing interactive workflows unchanged
