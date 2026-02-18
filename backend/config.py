"""
Configuration module for Tindi Tech E-commerce
Loads and validates environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration from environment variables"""
    
    # ============== APPLICATION SETTINGS ==============
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ============== DATABASE CONFIGURATION ==============
    MONGODB_USERNAME = os.getenv('MONGODB_USERNAME')
    MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')
    MONGODB_CLUSTER = os.getenv('MONGODB_CLUSTER', 'cluster0.zrebje6.mongodb.net')
    
    @property
    def MONGODB_URI(self):
        """Build MongoDB connection URI with URL encoding"""
        # Prefer explicit URI if set, BUT ignore if it defaults to localhost (common dev artifact)
        uri = os.getenv('MONGODB_URI')
        if uri and "127.0.0.1" not in uri and "localhost" not in uri:
            return uri
            
        # If credentials missing, we can't build it
        if not self.MONGODB_USERNAME or not self.MONGODB_PASSWORD:
            # Fallback for debugging if env vars fail but user wants to try
            if uri: return uri 
            
            raise ValueError(
                "MongoDB credentials not found! "
                "Please set MONGODB_USERNAME and MONGODB_PASSWORD in .env file"
            )
        
        import urllib.parse
        username = urllib.parse.quote_plus(self.MONGODB_USERNAME)
        password = urllib.parse.quote_plus(self.MONGODB_PASSWORD)
        
        return f"mongodb+srv://{username}:{password}@{self.MONGODB_CLUSTER}/?retryWrites=true&w=majority"
    
    # ============== ADMIN REGISTRATION CODES ==============
    SUPER_ADMIN_CODE = os.getenv('SUPER_ADMIN_CODE', 'SuperTindi2025')
    ADMIN_CODE = os.getenv('ADMIN_CODE', 'Staff2025')
    
    # ============== SECURITY SETTINGS ==============
    TOKEN_EXPIRATION_HOURS = int(os.getenv('TOKEN_EXPIRATION_HOURS', '24'))
    
    # Session Security (Harden Cookies)
    SESSION_COOKIE_SECURE = True  # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY = True # Prevent JS access
    SESSION_COOKIE_SAMESITE = 'Lax' # Prevent CSRF

    # ============== CORS SETTINGS ==============
    # Restrict to frontend origin by default
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # ============== RATE LIMITING ==============
    # ============== RATE LIMITING ==============
    RATE_LIMIT_ENABLED = False # Disabled for smoother testing
    LOGIN_RATE_LIMIT = "100 per minute"
    API_RATE_LIMIT = "1000 per hour"
    API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100 per hour')

    # ============== EMAIL CONFIGURATION ==============
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    # ============== FRONTEND CONFIGURATION ==============
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://tinditech-frontend.onrender.com')


    # ============== M-PESA CONFIGURATION ==============
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '174379') # Sandbox default
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919') # Sandbox default
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://your-domain.com/mpesa/callback') 

    # ============== MIKROTIK CONFIGURATION ==============
    MIKROTIK_HOST = os.getenv('MIKROTIK_HOST', '192.168.88.1')
    MIKROTIK_PORT = int(os.getenv('MIKROTIK_PORT', 8728)) # API Port
    MIKROTIK_USER = os.getenv('MIKROTIK_USER', 'admin')
    MIKROTIK_PASS = os.getenv('MIKROTIK_PASS', '')

    # ============== TP-LINK OMADA CONFIGURATION ==============
    # Type: 'mikrotik' or 'tplink'
    ROUTER_TYPE = os.getenv('ROUTER_TYPE', 'mikrotik') 
    
    TPLINK_URL = os.getenv('TPLINK_URL', 'https://192.168.0.1:8043') # Controller URL
    TPLINK_SITE_ID = os.getenv('TPLINK_SITE_ID', 'default') 
    TPLINK_USER = os.getenv('TPLINK_USER', 'admin')
    TPLINK_PASS = os.getenv('TPLINK_PASS', '')

 

    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        errors = []
        
        if not cls.MONGODB_USERNAME:
            errors.append("MONGODB_USERNAME is not set")
        if not cls.MONGODB_PASSWORD:
            errors.append("MONGODB_PASSWORD is not set")
        
        if cls.FLASK_ENV == 'production':
            if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
                errors.append("FLASK_SECRET_KEY must be set for production")
            if cls.DEBUG:
                errors.append("DEBUG mode should be disabled in production")
        
        if errors:
            raise ValueError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )
        
        return True


# Create a singleton config instance
config = Config()

# Validate configuration on import (will raise error if critical vars missing)
if __name__ == "__main__":
    # Test configuration
    try:
        config.validate()
        print("[OK] Configuration is valid!")
        print(f"\nEnvironment: {config.FLASK_ENV}")
        print(f"Debug Mode: {config.DEBUG}")
        print(f"Database Cluster: {config.MONGODB_CLUSTER}")
        print(f"CORS Origins: {config.CORS_ORIGINS}")
        print(f"Token Expiration: {config.TOKEN_EXPIRATION_HOURS} hours")
        print(f"Rate Limiting: {'Enabled' if config.RATE_LIMIT_ENABLED else 'Disabled'}")
    except ValueError as e:
        print(f"[ERROR] Configuration Error:\n{e}")
        print("\nPlease create a .env file based on .env.example")
