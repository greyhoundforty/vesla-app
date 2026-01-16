#!/usr/bin/env python3
"""Create DNS record for api.vesla-app.site"""

import yaml
from dns_manager import DNSManager

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create DNS manager
dns = DNSManager(config['digitalocean']['api_token'])

# Create A record for api.vesla-app.site
result = dns.create_a_record('api', 'vesla-app.site', '150.238.30.243')

if result:
    print("✓ Created DNS A record for api.vesla-app.site -> 150.238.30.243")
else:
    print("✗ Failed to create DNS record")
