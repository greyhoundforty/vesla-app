#!/bin/bash
# Fix permissions for Traefik running as vesla user

set -e

echo "Fixing ownership and permissions for Traefik..."

# Change ownership of letsencrypt and logs to vesla:docker
chown -R vesla:docker /opt/vesla/traefik/letsencrypt
chown -R vesla:docker /opt/vesla/traefik/logs

# Fix directory permissions (directories need execute permission)
chmod 700 /opt/vesla/traefik/letsencrypt
chmod 755 /opt/vesla/traefik/logs

# Create acme.json if it doesn't exist, with correct permissions
if [ ! -f /opt/vesla/traefik/letsencrypt/acme.json ]; then
    touch /opt/vesla/traefik/letsencrypt/acme.json
    chmod 600 /opt/vesla/traefik/letsencrypt/acme.json
    chown vesla:docker /opt/vesla/traefik/letsencrypt/acme.json
    echo "Created acme.json"
else
    # Fix permissions on existing acme.json
    chmod 600 /opt/vesla/traefik/letsencrypt/acme.json
    chown vesla:docker /opt/vesla/traefik/letsencrypt/acme.json
    echo "Fixed acme.json permissions"
fi

echo "Permissions fixed successfully!"
echo ""
echo "Directory permissions:"
ls -ld /opt/vesla/traefik/letsencrypt
ls -ld /opt/vesla/traefik/logs
echo ""
echo "acme.json permissions:"
ls -l /opt/vesla/traefik/letsencrypt/acme.json
