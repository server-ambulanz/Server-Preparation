import os
import sys
from typing import Optional
import CloudFlare
from dotenv import load_dotenv
import dns.resolver
import time

def load_config() -> tuple:
    """Load configuration from environment variables."""
    load_dotenv()
    
    api_token = os.getenv('CLOUDFLARE_API_TOKEN')
    zone_id = os.getenv('CLOUDFLARE_ZONE_ID')
    domain = os.getenv('DOMAIN')
    
    if not all([api_token, zone_id, domain]):
        raise ValueError("Missing required environment variables")
    
    return api_token, zone_id, domain

def get_existing_records(cf: CloudFlare.CloudFlare, zone_id: str) -> list:
    """Fetch all DNS records from Cloudflare."""
    try:
        dns_records = cf.zones.dns_records.get(zone_id)
        return dns_records
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print(f"Error fetching DNS records: {e}")
        sys.exit(1)

def extract_srv_numbers(records: list, domain: str) -> set:
    """Extract existing srv numbers from DNS records."""
    existing_numbers = set()
    
    for record in records:
        if record['type'] == 'A':
            name = record['name']
            if name.startswith('srv') and name.endswith(domain):
                try:
                    num = name.replace(f'.{domain}', '').replace('srv', '')
                    if num.isdigit():
                        existing_numbers.add(int(num))
                except ValueError:
                    continue
    
    return existing_numbers

def find_next_available_number(existing_numbers: set) -> Optional[int]:
    """Find the next available srv number."""
    # Start from 100 (excluding 1-99)
    current = 100
    
    while current <= 999:
        if current not in existing_numbers:
            return current
        current += 1
    
    # If we reach 999, return 1000
    if current > 999:
        return 1000
    
    return None

def main():
    # Load configuration
    api_token, zone_id, domain = load_config()
    
    # Initialize Cloudflare client
    cf = CloudFlare.CloudFlare(token=api_token)
    
    # Get existing records
    records = get_existing_records(cf, zone_id)
    
    # Extract existing srv numbers
    existing_numbers = extract_srv_numbers(records, domain)
    
    # Find next available number
    next_number = find_next_available_number(existing_numbers)
    
    if next_number is None:
        print("No available srv numbers found")
        return
    
    # Format the new subdomain
    new_subdomain = f"srv{str(next_number).zfill(3)}.{domain}"
    print(f"Next available subdomain: {new_subdomain}")

if __name__ == "__main__":
    main()