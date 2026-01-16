"""
DNS Manager for Vesla
Handles DNS record creation and management via Digital Ocean API
"""

import logging
import requests
import time
from typing import Optional

logger = logging.getLogger(__name__)


class DNSManager:
    """Manages DNS records via Digital Ocean API"""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.digitalocean.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def create_a_record(self, subdomain: str, domain: str, ip_address: str) -> bool:
        """
        Create an A record for subdomain.domain pointing to ip_address

        Args:
            subdomain: Subdomain name (e.g., 'myapp')
            domain: Base domain (e.g., 'vesla-app.site')
            ip_address: Server IP address

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/domains/{domain}/records"

        data = {
            "type": "A",
            "name": subdomain,
            "data": ip_address,
            "ttl": 300  # 5 minutes
        }

        try:
            logger.info(f"Creating DNS A record: {subdomain}.{domain} -> {ip_address}")
            response = requests.post(url, json=data, headers=self.headers)

            if response.status_code == 201:
                logger.info(f"Successfully created A record for {subdomain}.{domain}")
                return True
            elif response.status_code == 422:
                # Record might already exist - check and update
                logger.warning(f"Record might already exist, attempting update")
                return self.update_a_record(subdomain, domain, ip_address)
            else:
                logger.error(f"Failed to create A record: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error creating DNS record: {str(e)}")
            return False

    def update_a_record(self, subdomain: str, domain: str, ip_address: str) -> bool:
        """Update an existing A record"""
        record_id = self.get_record_id(subdomain, domain)
        if not record_id:
            logger.error(f"Could not find record ID for {subdomain}.{domain}")
            return False

        url = f"{self.base_url}/domains/{domain}/records/{record_id}"
        data = {
            "data": ip_address,
            "ttl": 300
        }

        try:
            response = requests.put(url, json=data, headers=self.headers)
            if response.status_code == 200:
                logger.info(f"Successfully updated A record for {subdomain}.{domain}")
                return True
            else:
                logger.error(f"Failed to update A record: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error updating DNS record: {str(e)}")
            return False

    def get_record_id(self, subdomain: str, domain: str) -> Optional[int]:
        """Get the record ID for a subdomain"""
        url = f"{self.base_url}/domains/{domain}/records"

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                records = response.json().get("domain_records", [])
                for record in records:
                    if record["type"] == "A" and record["name"] == subdomain:
                        return record["id"]
            return None
        except Exception as e:
            logger.error(f"Error getting record ID: {str(e)}")
            return None

    def delete_a_record(self, subdomain: str, domain: str) -> bool:
        """Delete an A record"""
        record_id = self.get_record_id(subdomain, domain)
        if not record_id:
            logger.warning(f"No record found for {subdomain}.{domain}")
            return False

        url = f"{self.base_url}/domains/{domain}/records/{record_id}"

        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"Successfully deleted A record for {subdomain}.{domain}")
                return True
            else:
                logger.error(f"Failed to delete A record: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error deleting DNS record: {str(e)}")
            return False

    def verify_dns_propagation(self, fqdn: str, expected_ip: str, max_attempts: int = 10) -> bool:
        """
        Verify DNS record has propagated

        Args:
            fqdn: Fully qualified domain name (e.g., 'myapp.vesla-app.site')
            expected_ip: Expected IP address
            max_attempts: Maximum verification attempts

        Returns:
            True if DNS resolves correctly, False otherwise
        """
        import socket

        for attempt in range(max_attempts):
            try:
                resolved_ip = socket.gethostbyname(fqdn)
                if resolved_ip == expected_ip:
                    logger.info(f"DNS propagated successfully: {fqdn} -> {resolved_ip}")
                    return True
                else:
                    logger.warning(f"DNS mismatch: {fqdn} resolves to {resolved_ip}, expected {expected_ip}")
            except socket.gaierror:
                logger.debug(f"DNS not yet propagated for {fqdn}, attempt {attempt + 1}/{max_attempts}")

            if attempt < max_attempts - 1:
                time.sleep(5)  # Wait 5 seconds between attempts

        logger.error(f"DNS propagation verification failed for {fqdn}")
        return False
