#!/usr/bin/env python3
"""
Quick script to create DNS A record for api.vesla-app.site
"""

import requests
import os

# Read token from traefik .env file
env_path = "/opt/vesla/traefik/.env"
do_token = None

with open(env_path) as f:
    for line in f:
        if line.startswith("DO_AUTH_TOKEN="):
            do_token = line.split("=", 1)[1].strip()
            break

if not do_token:
    print("Error: Could not find DO_AUTH_TOKEN in .env file")
    exit(1)

# Server details
SERVER_IP = "150.238.30.243"
SUBDOMAIN = "api"
DOMAIN = "vesla-app.site"

# Digital Ocean API
headers = {
    "Authorization": f"Bearer {do_token}",
    "Content-Type": "application/json"
}

url = f"https://api.digitalocean.com/v2/domains/{DOMAIN}/records"

data = {
    "type": "A",
    "name": SUBDOMAIN,
    "data": SERVER_IP,
    "ttl": 300
}

print(f"Creating DNS A record: {SUBDOMAIN}.{DOMAIN} -> {SERVER_IP}")

response = requests.post(url, json=data, headers=headers)

if response.status_code == 201:
    print("✓ DNS record created successfully!")
    print(f"  {SUBDOMAIN}.{DOMAIN} -> {SERVER_IP}")
    print("\nWait 1-2 minutes for DNS propagation, then test:")
    print(f"  dig @8.8.8.8 {SUBDOMAIN}.{DOMAIN} +short")
elif response.status_code == 422:
    print("⚠ Record might already exist. Checking...")

    # Get existing records
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        records = response.json().get("domain_records", [])
        for record in records:
            if record["type"] == "A" and record["name"] == SUBDOMAIN:
                print(f"✓ Record already exists: {SUBDOMAIN}.{DOMAIN} -> {record['data']}")
                if record['data'] != SERVER_IP:
                    print(f"  WARNING: Points to {record['data']}, expected {SERVER_IP}")
                break
else:
    print(f"✗ Error: {response.status_code}")
    print(response.text)
