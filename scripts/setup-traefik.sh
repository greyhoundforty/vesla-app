#!/bin/bash

################################################################################
# Setup Traefik Configuration
# Generates domain-specific Traefik configuration
################################################################################

set -euo pipefail

INSTALL_DIR="${1:-.}"
DOMAINS="${2:-}"
DO_TOKEN="${3:-}"
ACME_EMAIL="${4:-}"

if [[ -z "$DOMAINS" ]]; then
    echo "Usage: setup-traefik.sh <install_dir> <domains> <do_token> <acme_email>"
    exit 1
fi

echo "Generating Traefik configuration for domains: $DOMAINS"

# Create config directory if needed
mkdir -p "$INSTALL_DIR/traefik/config"

# Convert comma-separated domains to YAML array
IFS=',' read -ra domains_array <<< "$DOMAINS"

# Build domains configuration
domains_config=""
for domain in "${domains_array[@]}"; do
    domain=$(echo "$domain" | xargs)  # Trim whitespace
    domains_config+="          - main: \"$domain\"
            sans:
              - \"*.$domain\"
"
done

# Update traefik.yml with domains
cat > "$INSTALL_DIR/traefik/traefik.yml" << 'EOF'
# Traefik Static Configuration
api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  
  websecure:
    address: ":443"
    http:
      tls:
        certResolver: digitalocean
        domains:
EOF

echo "$domains_config" >> "$INSTALL_DIR/traefik/traefik.yml"

cat >> "$INSTALL_DIR/traefik/traefik.yml" << 'EOF'
  metrics:
    address: ":8082"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: vesla-network
  
  file:
    directory: "/etc/traefik/config"
    watch: true

certificatesResolvers:
  digitalocean:
    acme:
      email: "${ACME_EMAIL}"
      storage: "/letsencrypt/acme.json"
      dnsChallenge:
        provider: digitalocean
        delayBeforeCheck: 0
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"

log:
  level: DEBUG
  filePath: "/var/log/traefik/traefik.log"

accessLog:
  filePath: "/var/log/traefik/access.log"
  bufferingSize: 100

metrics:
  prometheus:
    buckets:
      - 0.1
      - 0.3
      - 1.2
      - 5.0
    addEntryPointsLabels: true
    addServicesLabels: true
    entryPoint: metrics
EOF

echo "✓ Traefik configuration generated"
