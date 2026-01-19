import requests
from config import config
import json

class OmadaBridge:
    def __init__(self):
        self.url = config.TPLINK_URL.rstrip('/')
        self.site_id = config.TPLINK_SITE_ID
        self.username = config.TPLINK_USER
        self.password = config.TPLINK_PASS
        self.session = requests.Session()
        self.token = None
        
        # Disable SSL warnings for self-signed controller certs
        requests.packages.urllib3.disable_warnings()

    def login(self):
        """Authenticate with Omada Controller."""
        try:
            # Omada API Login
            payload = {"username": self.username, "password": self.password}
            res = self.session.post(
                f"{self.url}/{self.site_id}/api/v2/login", 
                json=payload, 
                verify=False,
                timeout=10
            )
            data = res.json()
            if data.get("errorCode") == 0:
                if config.DEBUG: print(f"[TPLINK] Logged in. Token: {self.token[:5]}...")
                return True
            else:
                if config.DEBUG: print(f"[TPLINK] Login Failed: {data}")
                return False
        except Exception as e:
            if config.DEBUG: print(f"[TPLINK] Connection Error: {e}")
            return False

    def authorize_client(self, mac_address, duration_minutes):
        """Authorize a client MAC for a specific duration."""
        if not self.token:
            if not self.login(): return False, "Login failed"

        try:
            # API endpoint to authorize client
            # Note: Endpoint structure varies by Omada version. Using v2 standard.
            endpoint = f"{self.url}/{self.site_id}/api/v2/hotspot/login" 
            # Or /api/v2/sites/{siteId}/hotspot/login depending on version
            
            # Simplified for typical Omada Controller External Portal Auth
            # Actually, standard Omada External Portal requires the Controller to call US back,
            # OR we call the controller to 'authorize' the client.
            # Using the 'Operator' API approach.
            
            payload = {
                "mac": mac_address,
                "period": duration_minutes,
                "auth_type": 1 # 1=Voucher/One-time
            }
            
            headers = {
                "Csrf-Token": self.token, # Sometimes needed
                "Content-Type": "application/json"
            }
            
            # Note: Omada API is complex. This is a generic implementation.
            # For specific Gateway API:
            # POST https://controller:8043/{site}/api/v2/hotspot/extPortal/auth
            
            real_endpoint = f"{self.url}/{self.site_id}/api/v2/hotspot/extPortal/auth"
            
            res = self.session.post(real_endpoint, json=payload, headers=headers, verify=False)
            data = res.json()
            
            if data.get("errorCode") == 0:
                if config.DEBUG: print(f"[TPLINK] Authorized {mac_address} for {duration_minutes} mins")
                return True, "Authorized"
            else:
                if config.DEBUG: print(f"[TPLINK] Auth Failed: {data}")
                return False, f"Omada Error: {data.get('msg')}"
                
        except Exception as e:
             if config.DEBUG: print(f"[TPLINK] Request Error: {e}")
             return False, str(e)

# Singleton
tplink = OmadaBridge()
