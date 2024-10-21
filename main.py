import os
import sys
import ipaddress
from typing import Optional
import CloudFlare
from dotenv import load_dotenv
import time

def check_root():
    """Überprüft, ob das Skript mit Root-Rechten ausgeführt wird."""
    if os.geteuid() != 0:
        print("This script must be run as root or with sudo privileges.")
        sys.exit(1)

def clear_screen():
    """Leert den Konsolenbildschirm."""
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config() -> tuple:
    """Lädt die Konfiguration aus den Umgebungsvariablen."""
    load_dotenv()
    
    api_token = os.getenv('CLOUDFLARE_API_TOKEN')
    zone_id = os.getenv('CLOUDFLARE_ZONE_ID')
    domain = os.getenv('DOMAIN')
    
    if not all([api_token, zone_id, domain]):
        raise ValueError("Missing required environment variables")
    
    return api_token, zone_id, domain

def get_existing_records(cf: CloudFlare.CloudFlare, zone_id: str) -> list:
    """Ruft alle DNS-Einträge von Cloudflare ab."""
    try:
        dns_records = cf.zones.dns_records.get(zone_id)
        return dns_records
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print(f"Error fetching DNS records: {e}")
        sys.exit(1)

def extract_srv_numbers(records: list, domain: str) -> set:
    """Extrahiert existierende srv-Nummern aus den DNS-Einträgen."""
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
    """Findet die nächste verfügbare srv-Nummer."""
    # Beginnt bei 100 (1-99 ausgeschlossen)
    current = 100
    
    while current <= 999:
        if current not in existing_numbers:
            return current
        current += 1
    
    # Wenn 999 erreicht ist, gib 1000 zurück
    if current > 999:
        return 1000
    
    return None

def is_valid_public_ip(ip: str) -> bool:
    """Prüft, ob die angegebene IP eine gültige öffentliche IPv4-Adresse ist."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_global and isinstance(ip_obj, ipaddress.IPv4Address)
    except ValueError:
        return False

def ip_exists_in_records(records: list, ip: str) -> bool:
    """Prüft, ob die angegebene IP bereits in den DNS-Einträgen existiert."""
    return any(record['type'] == 'A' and record['content'] == ip for record in records)

def add_dns_record(cf: CloudFlare.CloudFlare, zone_id: str, domain: str, subdomain: str, ip: str):
    """Fügt einen neuen DNS A-Eintrag zu Cloudflare hinzu."""
    record = {
        'type': 'A',
        'name': subdomain,
        'content': ip,
        'proxied': False
    }
    try:
        cf.zones.dns_records.post(zone_id, data=record)
        print(f"Successfully added DNS record for {subdomain}.{domain} pointing to {ip}")
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print(f"Error adding DNS record: {e}")
        sys.exit(1)

def main():
    # Überprüfung der Root-Rechte
    check_root()

    # Bildschirm leeren
    clear_screen()
    
    print("=== DNS Checker and IP Management Script ===\n")
    
    # Konfiguration laden
    api_token, zone_id, domain = load_config()
    
    # Cloudflare-Client initialisieren
    cf = CloudFlare.CloudFlare(token=api_token)
    
    # Vorhandene Einträge abrufen
    records = get_existing_records(cf, zone_id)
    
    # IP-Adresse vom Benutzer abfragen
    while True:
        ip = input("Please enter the IP address of the server: ").strip()
        if is_valid_public_ip(ip):
            break
        else:
            print("Invalid IP address. Please enter a valid public IPv4 address.")
    
    # Prüfen, ob IP bereits in Einträgen existiert
    if ip_exists_in_records(records, ip):
        print(f"Error: The IP address {ip} is already registered in the DNS records.")
        sys.exit(1)
    
    # Vorhandene srv-Nummern extrahieren
    existing_numbers = extract_srv_numbers(records, domain)
    
    # Nächste verfügbare Nummer finden
    next_number = find_next_available_number(existing_numbers)
    
    if next_number is None:
        print("No available srv numbers found")
        return
    
    # Neue Subdomain formatieren
    new_subdomain = f"srv{str(next_number).zfill(3)}"
    full_domain = f"{new_subdomain}.{domain}"
    
    # Neuen DNS-Eintrag hinzufügen
    add_dns_record(cf, zone_id, domain, new_subdomain, ip)
    
    print(f"\nSuccessfully added new server:")
    print(f"Subdomain: {full_domain}")
    print(f"IP Address: {ip}")

if __name__ == "__main__":
    main()