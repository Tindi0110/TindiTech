import os
from gotrue import SyncGoTrueClient
from config import config

# Initialize Supabase Auth Client
# We'll use Gotrue directly as it has fewer dependencies than the full supabase SDK
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY") # This should be the anon/public key

auth: SyncGoTrueClient = None

def init_supabase_auth():
    global auth
    if url and key:
        try:
            # Construct the Gotrue URL from the Supabase URL
            # Usually it's {SUPABASE_URL}/auth/v1
            auth_url = f"{url.rstrip('/')}/auth/v1"
            auth = SyncGoTrueClient(url=auth_url, headers={"apikey": key})
            print("[Supabase Auth] Client initialized successfully")
        except Exception as e:
            print(f"[Supabase Auth] Initialization failed: {e}")
    else:
        print("[Supabase Auth] URL or KEY missing in Config/Env")

# Call init on module load
init_supabase_auth()

def create_supabase_user(email, password, data=None):
    """Register a new user in Supabase Auth"""
    if not auth: return None, "Supabase Auth not initialized"
    try:
        res = auth.sign_up(email=email, password=password, data=data or {})
        return res, None
    except Exception as e:
        return None, str(e)

def login_supabase_user(email, password):
    """Login user via Supabase Auth"""
    if not auth: return None, "Supabase Auth not initialized"
    try:
        res = auth.sign_in_with_password(email=email, password=password)
        return res, None
    except Exception as e:
        return None, str(e)

def verify_token(token):
    """Verify a Supabase JWT and return the user"""
    if not auth: return None
    try:
        return auth.get_user(token)
    except Exception:
        return None
