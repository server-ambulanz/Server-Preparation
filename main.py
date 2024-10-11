import requests
import re
from datetime import datetime, timedelta
from config import Config
import colorlog
import logging
import sys

def setup_logger():
    """Konfiguriert das farbige Logging"""
    handler = colorlog.StreamHandler(sys.stdout)
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    ))

    logger = colorlog.getLogger('CloudflareChecker')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Entferne Standard-Handler falls vorhanden
    logger.propagate = False
    
    return logger

logger = setup_logger()

class AkeylessClient:
    def __init__(self):
        self.access_id = Config.AKEYLESS_ACCESS_ID
        self.access_key = Config.AKEYLESS_ACCESS_KEY
        self.api_url = Config.AKEYLESS_API_URL
        self._token = None
        self._token_expiry = None
        
        # Session mit Retry-Mechanismus
        self.session = requests.Session()
        retries = requests.adapters.Retry(
            total=Config.API_RETRIES,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
        logger.debug("AkeylessClient initialisiert")

    def _get_auth_token(self):
        """Authentifizierung gegen Akeyless und Token abrufen"""
        try:
            logger.info("🔑 Hole neuen Akeyless Auth Token...")
            auth_data = {
                "access-type": "access_key",
                "access-id": self.access_id,
                "access-key": self.access_key
            }
            
            response = self.session.post(
                f"{self.api_url}/auth",
                json=auth_data,
                timeout=Config.API_TIMEOUT
            )
            
            response.raise_for_status()
            result = response.json()
            
            self._token = result['token']
            self._token_expiry = datetime.now() + timedelta(minutes=60)
            logger.info("✅ Akeyless Token erfolgreich aktualisiert")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Fehler bei der Akeyless Authentifizierung: {e}")
            raise

    def _ensure_valid_token(self):
        """Stellt sicher, dass ein gültiger Token vorhanden ist"""
        if not self._token or not self._token_expiry or datetime.now() >= self._token_expiry:
            self._get_auth_token()

    def get_secret(self, secret_path):
        """Secret von Akeyless abrufen"""
        self._ensure_valid_token()
        
        try:
            logger.info(f"🔍 Rufe Secret ab: {secret_path}")
            get_secret_data = {
                "token": self._token,
                "name": secret_path,
            }
            
            response = self.session.post(
                f"{self.api_url}/get-secret-value",
                json=get_secret_data,
                timeout=Config.API_TIMEOUT
            )
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Secret erfolgreich abgerufen: {secret_path}")
            return result['value']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Fehler beim Abrufen des Secrets {secret_path}: {e}")
            raise

class CloudflareServerChecker:
    def __init__(self, auth_token, zone_id):
        self.auth_token = auth_token
        self.zone_id = zone_id
        self.base_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Session mit Retry-Mechanismus
        self.session = requests.Session()
        retries = requests.adapters.Retry(
            total=Config.API_RETRIES,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
        logger.debug("CloudflareServerChecker initialisiert")

    def get_all_records(self):
        """Alle DNS-Records von Cloudflare abrufen"""
        records = []
        page = 1
        per_page = 100
        
        try:
            logger.info("📡 Rufe DNS-Records von Cloudflare ab...")
            while True:
                params = {
                    "page": page,
                    "per_page": per_page
                }
                
                response = self.session.get(
                    self.base_url,
                    headers=self.headers,
                    params=params,
                    timeout=Config.API_TIMEOUT
                )
                
                response.raise_for_status()
                data = response.json()
                page_records = data["result"]
                records.extend(page_records)
                
                if len(page_records) < per_page:
                    break
                    
                page += 1
            
            logger.info(f"✅ {len(records)} DNS-Records erfolgreich abgerufen")
            return records
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Fehler beim Abrufen der DNS-Records: {e}")
            raise

    def find_next_available_number(self):
        """Nächste verfügbare Servernummer finden"""
        records = self.get_all_records()
        used_numbers = set()
        
        logger.info("🔍 Suche nach der nächsten verfügbaren Servernummer...")
        for record in records:
            match = re.match(Config.DOMAIN_PATTERN, record["name"])
            if match:
                used_numbers.add(int(match.group(1)))
        
        for i in range(1000):
            if i not in used_numbers:
                next_number = f"{i:03d}"
                logger.info(f"✅ Nächste verfügbare Nummer gefunden: {next_number}")
                return next_number
        
        logger.error("❌ Keine verfügbaren Nummern mehr")
        raise Exception("Keine verfügbaren Nummern mehr (000-999 sind alle vergeben)")

def main():
    try:
        logger.info("🚀 Starte Server-Nummer-Checker...")
        
        # Akeyless Client initialisieren
        akeyless_client = AkeylessClient()
        
        # Secrets von Akeyless abrufen
        auth_token = akeyless_client.get_secret(Config.CLOUDFLARE_TOKEN_PATH)
        zone_id = akeyless_client.get_secret(Config.CLOUDFLARE_ZONE_ID_PATH)
        
        # CloudflareServerChecker initialisieren
        checker = CloudflareServerChecker(auth_token, zone_id)
        
        # Nächste verfügbare Nummer finden
        next_number = checker.find_next_available_number()
        logger.info(f"🎉 Ergebnis: srv{next_number}.serverambulanz.com")
        
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler im Hauptprogramm: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()