import routeros_api
from config import config

class MikrotikBridge:
    def __init__(self):
        self.host = config.MIKROTIK_HOST
        self.username = config.MIKROTIK_USER
        self.password = config.MIKROTIK_PASS
        self.port = config.MIKROTIK_PORT
        self.connection = None

    def connect(self):
        try:
            self.connection = routeros_api.RouterOsApiPool(
                self.host, 
                username=self.username, 
                password=self.password,
                port=self.port,
                plaintext_login=True 
            )
            return self.connection.get_api()
        except Exception as e:
            if config.DEBUG: print(f"[MIKROTIK] Connection Failed: {e}")
            return None

    def add_hotspot_user(self, username, password, profile="default", limit_uptime=None):
        """
        Add a user to MikroTik Hotspot.
        limit_uptime: String "1h", "30m", etc. or None
        """
        api = self.connect()
        if not api: return False, "Connection failed"

        try:
            hotspot_users = api.get_resource('/ip/hotspot/user')
            
            # Check if exists
            existing = hotspot_users.get(name=username)
            if existing:
                # Update existing? Or Error? Let's update.
                params = {}
                if limit_uptime: params['limit-uptime'] = limit_uptime
                if profile: params['profile'] = profile
                
                hotspot_users.set(id=existing[0]['id'], **params)
                if config.DEBUG: print(f"[MIKROTIK] Updated user {username}")
            else:
                # Create New
                params = {
                    'name': username,
                    'password': password,
                    'profile': profile
                }
                if limit_uptime: params['limit-uptime'] = limit_uptime
                
                hotspot_users.add(**params)
                if config.DEBUG: print(f"[MIKROTIK] Created user {username}")
                
            return True, "User authorized on Router"
            
        except Exception as e:
            if config.DEBUG: print(f"[MIKROTIK] Error adding user: {e}")
            return False, str(e)
        finally:
            if self.connection: self.connection.disconnect()

    def remove_user(self, username):
        api = self.connect()
        if not api: return
        try:
            list_users = api.get_resource('/ip/hotspot/user')
            list_users.remove(name=username)
        except:
            pass
        finally:
            if self.connection: self.connection.disconnect()

# Singleton
mikrotik = MikrotikBridge()
