import requests
import json
import uuid
import sys

# Usage: python simulate_callback.py <CheckoutRequestID> <Amount> [Phone]
# If CheckoutRequestID is not provided, it will prompt or fail if specifically testing an order.

def simulate_callback(checkout_id, amount=100, phone="254712345678", result_code=0):
    url = "http://localhost:5000/api/mpesa/callback"
    
    # Payload matching Safaricom's structure
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": f"req_{uuid.uuid4()}",
                "CheckoutRequestID": checkout_id,
                "ResultCode": result_code,
                "ResultDesc": "The service request is processed successfully." if result_code == 0 else "Request cancelled by user",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": amount},
                        {"Name": "MpesaReceiptNumber", "Value": f"SIM{uuid.uuid4().hex[:10].upper()}"},
                        {"Name": "TransactionDate", "Value": 20250117130000},
                        {"Name": "PhoneNumber", "Value": int(phone)}
                    ]
                }
            }
        }
    }
    
    if result_code != 0:
        del payload["Body"]["stkCallback"]["CallbackMetadata"]

    print(f"Sending Callback for ID: {checkout_id}...")
    try:
        res = requests.post(url, json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simulate_callback.py <CheckoutRequestID> [Amount] [Phone] [ResultCode]")
        print("Example: python simulate_callback.py ws_CO_DM_123456 1500")
    else:
        cid = sys.argv[1]
        amt = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        ph = sys.argv[3] if len(sys.argv) > 3 else "254712345678"
        rc = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        simulate_callback(cid, amt, ph, rc)
