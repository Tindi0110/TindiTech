import requests
from pymongo import MongoClient
import certifi

# Database Config (matching backend/config.py or .env)
# Assuming defaults since I don't have the .env content handy but I saw the connection string in main.py
# Wait, main.py uses config.MONGODB_URI.
# I need to read .env to get the URI or use the default local one?
# backend/.env was listed but not read fully.
# backend/main.py: client = MongoClient(config.MONGODB_URI, tlsCAFile=certifi.where())

# I will assume the server is running locally and I can connect to it.
# Actually I'll just use the `verify-account` endpoint if I can get the OTP.
# But modifying the DB is robust.

# Let's try to verify via API using the OTP I saw in the logs first?
# The OTP was 437269 for test@example.com (from Step 335)
# Wait, that might expire or be for a different run?
# I saw it in the logs for the run I just did.

API_URL = "http://127.0.0.1:5000"

def verify_and_login():
    email = "test@example.com"
    otp = "437269" # From logs

    print(f"Verifying {email} with OTP {otp}...")
    verify_data = {
        "email": email,
        "email_otp": otp
    }
    
    try:
        res = requests.post(f"{API_URL}/verify-account", json=verify_data)
        print(f"Verification Status: {res.status_code}")
        print(f"Verification Response: {res.text}")
        
        if res.status_code == 200:
            print("\nLogin attempt after verification...")
            login_data = {
                "username": "testuser",
                "password": "password123",
                "remember": False
            }
            login_res = requests.post(f"{API_URL}/login", json=login_data)
            print(f"Login Status: {login_res.status_code}")
            print(f"Login Response: {login_res.text}")
        else:
            print("Verification failed. Cannot proceed to login test.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_and_login()
