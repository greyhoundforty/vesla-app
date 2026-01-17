#!/bin/bash

################################################################################
# Setup API Server Configuration
# Generates API server environment configuration
################################################################################

set -euo pipefail

INSTALL_DIR="${1:-.}"
DO_TOKEN="${2:-}"
ACME_EMAIL="${3:-}"

if [[ -z "$DO_TOKEN" ]] || [[ -z "$ACME_EMAIL" ]]; then
    echo "Usage: setup-api-server.sh <install_dir> <do_token> <acme_email>"
    exit 1
fi

echo "Generating API server configuration"

# Generate random API token
API_TOKEN=$(openssl rand -hex 32)

# Create .env file
cat > "$INSTALL_DIR/server/.env" << EOF
# Vesla Server Configuration
FLASK_ENV=production
API_TOKEN=$API_TOKEN
DO_AUTH_TOKEN=$DO_TOKEN
ACME_EMAIL=$ACME_EMAIL
EOF

chmod 600 "$INSTALL_DIR/server/.env"

echo "✓ API server configuration generated"
echo "API Token: $API_TOKEN"
