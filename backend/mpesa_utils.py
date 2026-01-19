import base64
import requests
import time
from datetime import datetime, timedelta
from config import config

# Token cache to avoid regenerating on every request
_token_cache = {"token": None, "expires_at": None}

def get_mpesa_password(shortcode, passkey):
    """Generates the password for STK Push"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = f"{shortcode}{passkey}{timestamp}"
    encoded_string = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    return encoded_string, timestamp

def get_access_token(consumer_key, consumer_secret, force_refresh=False):
    """Generates OAuth access token from Daraja API with caching"""
    
    # Check cache first (tokens valid for ~1 hour, we cache for 50 min)
    if not force_refresh and _token_cache["token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            if config.DEBUG: print("[M-PESA] Using cached access token")
            return _token_cache["token"]
    
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        if config.DEBUG: print("[M-PESA] Generating new access token...")
        # Add timeout: 5s connection, 10s read
        response = requests.get(api_url, auth=(consumer_key, consumer_secret), timeout=(5, 10))
        response.raise_for_status()
        result = response.json()
        token = result['access_token']
        
        # Cache token for 50 minutes (expires in 60)
        _token_cache["token"] = token
        _token_cache["expires_at"] = datetime.now() + timedelta(minutes=50)
        if config.DEBUG: print("[M-PESA] Token generated and cached successfully")
        
        return token
    except requests.Timeout:
        if config.DEBUG: print("[M-PESA] Timeout while generating access token")
        return None
    except requests.RequestException as e:
        if config.DEBUG: print(f"[M-PESA] Error generating access token: {e}")
        return None

def initiate_stk_push(phone_number, amount, account_reference="TindiTech", transaction_desc="Order Payment"):
    """Initiates an STK Push to the customer's phone with retry logic"""
    
    # 1. Get Configs
    consumer_key = config.MPESA_CONSUMER_KEY
    consumer_secret = config.MPESA_CONSUMER_SECRET
    shortcode = config.MPESA_SHORTCODE
    passkey = config.MPESA_PASSKEY
    callback_url = config.MPESA_CALLBACK_URL
    
    if not all([consumer_key, consumer_secret, shortcode, passkey]):
        return {"success": False, "error": "M-Pesa credentials missing in config"}

    # 2. Validation & Simulation Check
    keys_are_placeholders = (
        "your_" in consumer_key or 
        "your_" in consumer_secret or 
        len(consumer_key) < 10
    )

    if keys_are_placeholders:
        # SIMULATION MODE: Return success immediately without calling Safaricom
        if config.DEBUG: print("[M-PESA] Using Simulation Mode (Real keys not set)")
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return {
            "success": True, 
            "message": "STK Push Simulation Successful", 
            "checkout_request_id": f"ws_CO_DM_{timestamp}_0000"
        }

    # 3. Get Access Token (with caching)
    access_token = get_access_token(consumer_key, consumer_secret)
    if not access_token:
        return {"success": False, "error": "Failed to generate access token - check M-Pesa credentials"}

    # 4. Generate Password
    password, timestamp = get_mpesa_password(shortcode, passkey)

    # 5. Prepare Request Headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # 6. Format phone number (Ensure 254...)
    phone_number = phone_number.replace('+', '').replace(' ', '').strip()
    
    # Handle 07... -> 2547...
    if phone_number.startswith('0') and len(phone_number) == 10:
        phone_number = '254' + phone_number[1:]
    # Handle 25407... -> 2547... (Common Double Prefix Error)
    elif phone_number.startswith('2540') and len(phone_number) == 13:
        phone_number = '254' + phone_number[4:]
    
    # Validate phone format
    if not phone_number.startswith('254') or len(phone_number) != 12:
        return {"success": False, "error": f"Invalid phone number format. Expected 254XXXXXXXXX, got {phone_number}"}

    # 7. Prepare Payload
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }

    # 8. Send Request with Retry Logic
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if config.DEBUG: print(f"[M-PESA] STK Push attempt {attempt + 1}/{max_retries}")
            
            # Add timeout: 5s connection, 15s read
            response = requests.post(api_url, json=payload, headers=headers, timeout=(5, 15))
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('ResponseCode') == '0':
                if config.DEBUG: print("[M-PESA] STK Push successful")
                return {
                    "success": True, 
                    "message": "STK Push initiated successfully", 
                    "checkout_request_id": response_data.get('CheckoutRequestID')
                }
            else:
                error_msg = response_data.get('errorMessage') or response_data.get('ResponseDescription', 'STK Push failed')
                if config.DEBUG: print(f"[M-PESA] STK Push failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.Timeout:
            if config.DEBUG: print(f"[M-PESA] Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = 0.5 * (attempt + 1)  # Exponential backoff: 0.5s, 1s
                if config.DEBUG: print(f"[M-PESA] Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return {"success": False, "error": "Request timeout - Safaricom API is slow. Please try again."}
            
        except requests.RequestException as e:
            if config.DEBUG: print(f"[M-PESA] Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 0.5 * (attempt + 1)
                if config.DEBUG: print(f"[M-PESA] Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return {"success": False, "error": f"Network error: {str(e)}. Check your internet connection."}
    
    # Should never reach here, but just in case
    return {"success": False, "error": "Maximum retries exceeded"}
