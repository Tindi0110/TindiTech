import urllib.parse
from pymongo import MongoClient
import certifi

def force_verify():
    username = urllib.parse.quote_plus("Njenga05")
    password = urllib.parse.quote_plus("Tindi@0110")
    cluster = "cluster0.zrebje6.mongodb.net"

    uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority"

    print(f"Connecting to DB...")
    try:
        client = MongoClient(uri, tlsCAFile=certifi.where())
        db = client["TindiTech"]
        users = db["users"]
        
        user_email = "test@example.com"
        print(f"Updating user {user_email}...")
        
        result = users.update_one(
            {"email": user_email},
            {"$set": {"is_email_verified": True, "is_phone_verified": True}}
        )
        
        print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")
        
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    force_verify()
