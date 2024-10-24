#!/bin/bash

# Globale Variablen für Farbausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vault Konfiguration
VAULT_ADDR="${VAULT_ADDR:-https://vault.example.com:8200}"
VAULT_PATH="secret/dns-manager"  # Pfad in Vault wo die Secrets liegen

# Signal Handler für Ctrl+C
trap ctrl_c INT

function ctrl_c() {
    echo -e "\n${RED}Ctrl+C pressed. Exiting gracefully.${NC}"
    exit 0
}

# Funktion zum Leeren des Bildschirms
clear_screen() {
    clear
}

# Prüft Root-Rechte
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}This script must be run as root or with sudo privileges.${NC}"
        exit 1
    fi
}

# Überprüft Vault-Verbindung und Authentifizierung
check_vault_connection() {
    if [ -z "$VAULT_ADDR" ]; then
        echo -e "${RED}VAULT_ADDR environment variable is not set.${NC}"
        exit 1
    fi

    if [ -z "$VAULT_TOKEN" ]; then
        echo -e "${RED}VAULT_TOKEN environment variable is not set.${NC}"
        exit 1
    fi

    # Überprüfe Vault-Status
    local vault_status
    vault_status=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/sys/health")

    if [ "$vault_status" != "200" ] && [ "$vault_status" != "429" ]; then
        echo -e "${RED}Unable to connect to Vault server. Status code: ${vault_status}${NC}"
        exit 1
    fi
}

# Lädt Secrets aus Vault‚
load_secrets() {
    echo -e "${YELLOW}Fetching secrets from Vault...${NC}"
    
    # Hole Secrets von Vault
    local response
    response=$(curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/${VAULT_PATH}/data/cloudflare")

    # Überprüfe die Antwort
    if ! echo "$response" | grep -q '"data"'; then
        echo -e "${RED}Failed to fetch secrets from Vault: $response${NC}"
        exit 1
    fi

    # Extrahiere die Secrets
    CLOUDFLARE_API_TOKEN=$(echo "$response" | jq -r '.data.data.api_token')
    CLOUDFLARE_ZONE_ID=$(echo "$response" | jq -r '.data.data.zone_id')
    DOMAIN=$(echo "$response" | jq -r '.data.data.domain')

    # Überprüfe, ob alle benötigten Secrets vorhanden sind
    if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ZONE_ID" ] || [ -z "$DOMAIN" ]; then
        echo -e "${RED}Missing required secrets in Vault.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Successfully loaded secrets from Vault.${NC}"
}

# Erkennt die Linux-Distribution
get_distribution() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    else
        echo "unknown"
    fi
}

# Aktualisiert die Paketquellen und installiert benötigte Pakete
update_system_and_check_dependencies() {
    local distro=$(get_distribution)
    echo -e "${YELLOW}Detected distribution: $distro${NC}"
    
    case "$distro" in
        "ubuntu"|"debian")
            echo -e "${YELLOW}Updating package sources...${NC}"
            apt-get update || {
                echo -e "${RED}Failed to update package sources.${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}Installing required packages...${NC}"
            apt-get install -y curl jq || {
                echo -e "${RED}Failed to install required packages.${NC}"
                exit 1
            }
            ;;
            
        "centos"|"rhel"|"fedora"|"rocky"|"almalinux")
            echo -e "${YELLOW}Updating package sources...${NC}"
            dnf check-update || yum check-update || {
                echo -e "${RED}Failed to update package sources.${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}Installing required packages...${NC}"
            dnf install -y curl jq || yum install -y curl jq || {
                echo -e "${RED}Failed to install required packages.${NC}"
                exit 1
            }
            ;;
            
        "opensuse"|"suse")
            echo -e "${YELLOW}Updating package sources...${NC}"
            zypper refresh || {
                echo -e "${RED}Failed to update package sources.${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}Installing required packages...${NC}"
            zypper install -y curl jq || {
                echo -e "${RED}Failed to install required packages.${NC}"
                exit 1
            }
            ;;
            
        "arch"|"manjaro")
            echo -e "${YELLOW}Updating package sources...${NC}"
            pacman -Sy || {
                echo -e "${RED}Failed to update package sources.${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}Installing required packages...${NC}"
            pacman -S --noconfirm curl jq || {
                echo -e "${RED}Failed to install required packages.${NC}"
                exit 1
            }
            ;;
            
        *)
            echo -e "${RED}Unsupported distribution. Please install curl and jq manually if needed.${NC}"
            if ! command -v curl &> /dev/null || ! command -v jq &> /dev/null; then
                echo -e "${RED}curl and jq are required but not installed.${NC}"
                exit 1
            fi
            ;;
    esac
    
    echo -e "${GREEN}System update completed and all dependencies are available.${NC}"
}

# Prüft, ob eine IP-Adresse gültig ist
is_valid_public_ip() {
    local ip=$1
    # Prüft IPv4 Format
    if [[ ! $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 1
    fi
    
    # Prüft, ob die Zahlen im gültigen Bereich sind
    local IFS='.'
    read -ra ADDR <<< "$ip"
    for i in "${ADDR[@]}"; do
        if [ $i -lt 0 ] || [ $i -gt 255 ]; then
            return 1
        fi
    done
    
    # Prüft, ob es sich um eine private IP handelt
    if [[ $ip =~ ^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.) ]]; then
        return 1
    fi
    
    # Prüft auf lokale und spezielle IPs
    if [[ $ip =~ ^(127\.|0\.|169\.254\.|224\.) ]]; then
        return 1
    fi
    
    return 0
}

# Prüft, ob eine IP bereits in den DNS-Einträgen existiert
check_existing_ip() {
    local ip=$1
    local response
    
    response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json")
    
    if echo "$response" | grep -q "\"content\":\"$ip\""; then
        return 0 # IP exists
    else
        return 1 # IP does not exist
    fi
}

# Findet die nächste verfügbare srv Nummer
find_next_srv_number() {
    local response
    local existing_numbers=()
    
    response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json")
    
    # Extrahiert alle existierenden srv Nummern
    while read -r number; do
        if [ ! -z "$number" ]; then
            existing_numbers+=($number)
        fi
    done < <(echo "$response" | grep -o 'srv[0-9]\{3\}' | grep -o '[0-9]\{3\}')
    
    # Findet die nächste verfügbare Nummer ab 100
    for ((i=100; i<=999; i++)); do
        if [[ ! " ${existing_numbers[@]} " =~ " ${i} " ]]; then
            echo $i
            return 0
        fi
    done
    
    echo "1000"
    return 0
}

# Fügt einen neuen DNS A-Record hinzu
add_dns_record() {
    local subdomain=$1
    local ip=$2
    local full_domain="${subdomain}.${DOMAIN}"
    
    local response
    response=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{
            \"type\": \"A\",
            \"name\": \"$subdomain\",
            \"content\": \"$ip\",
            \"proxied\": false
        }")
    
    if echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}Successfully added DNS record for ${full_domain} pointing to ${ip}${NC}"
        return 0
    else
        echo -e "${RED}Error adding DNS record: $response${NC}"
        return 1
    fi
}

# Hauptfunktion
main() {
    check_root
    clear_screen
    
    echo -e "=== DNS Checker and IP Management Script ===\n"
    
    # System aktualisieren und Abhängigkeiten überprüfen
    update_system_and_check_dependencies
    
    # Vault-Verbindung überprüfen
    check_vault_connection
    
    # Secrets von Vault laden
    load_secrets
    
    # IP-Adresse abfragen (max. 3 Versuche)
    attempts=0
    while [ $attempts -lt 3 ]; do
        read -p "Please enter the IP address of the server: " ip
        
        if is_valid_public_ip "$ip"; then
            if check_existing_ip "$ip"; then
                clear_screen
                echo -e "${RED}Error: The IP address $ip is already registered in the DNS records.${NC}"
                echo "Please contact support for assistance with this issue."
                echo "Exiting the script."
                exit 1
            fi
            break
        else
            attempts=$((attempts + 1))
            clear_screen
            echo -e "${RED}Error: Invalid IP address. Please enter a valid public IPv4 address.${NC}"
            if [ $attempts -lt 3 ]; then
                echo "Attempts remaining: $((3 - attempts))"
            else
                echo "Maximum attempts reached. Exiting."
                exit 1
            fi
        fi
    done
    
    # Nächste verfügbare srv Nummer finden
    next_number=$(find_next_srv_number)
    if [ -z "$next_number" ]; then
        echo -e "${RED}No available srv numbers found${NC}"
        exit 1
    fi
    
    # Neue Subdomain erstellen
    new_subdomain="srv$(printf "%03d" $next_number)"
    
    # DNS-Eintrag hinzufügen
    if add_dns_record "$new_subdomain" "$ip"; then
        echo -e "\n${GREEN}Successfully added new server:${NC}"
        echo "Subdomain: ${new_subdomain}.${DOMAIN}"
        echo "IP Address: ${ip}"
    fi
}

# Skript ausführen
main