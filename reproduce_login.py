import requests

API_URL = "http://127.0.0.1:5000"

def test_invalid_login():
    print(f"Testing Invalid Login against {API_URL}...")
    try:
        # Login with wrong password
        login_data = {
            "username": "testuser",
            "password": "wrongpassword123", # Wrong
            "remember": False
        }
        print("\nLogging in with wrong password...")
        login_res = requests.post(f"{API_URL}/login", json=login_data)
        print(f"Login Status: {login_res.status_code}")
        print(f"Login Response: {login_res.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_invalid_login()
