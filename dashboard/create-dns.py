#!/usr/bin/env python3
"""Create DNS record for dashboard.vesla-app.site"""

import sys
sys.path.append('/opt/vesla/server')

import yaml
from dns_manager import DNSManager

# Load config from server
with open('/opt/vesla/server/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create DNS manager
dns = DNSManager(config['digitalocean']['api_token'])

# Create A record for dashboard.vesla-app.site
result = dns.create_a_record('dashboard', 'vesla-app.site', '150.238.30.243')

if result:
    print("✓ Created DNS A record for dashboard.vesla-app.site -> 150.238.30.243")
else:
    print("✗ Failed to create DNS record")
