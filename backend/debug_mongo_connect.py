import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse
import sys
import certifi

# Load .env
load_dotenv()

print("--- MongoDB Connection Tester ---")

username = os.getenv('MONGODB_USERNAME')
password = os.getenv('MONGODB_PASSWORD')
cluster = os.getenv('MONGODB_CLUSTER')

if not username or not password:
    print("ERROR: Missing MONGODB_USERNAME or MONGODB_PASSWORD in .env")
    sys.exit(1)

print(f"Username: {username}")
print(f"Cluster: {cluster}")

try:
    escaped_username = urllib.parse.quote_plus(username)
    escaped_password = urllib.parse.quote_plus(password)
    uri = f"mongodb+srv://{escaped_username}:{escaped_password}@{cluster}/?retryWrites=true&w=majority"
    
    print(f"Certifi Path: {certifi.where()}")
    print("Attempting to connect...")
    client = MongoClient(uri, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
    
    # Force a network call
    client.admin.command('ping')
    print("SUCCESS: Connected to MongoDB!")
    
    # List databases
    dbs = client.list_database_names()
    print(f"Databases found: {dbs}")
    
except Exception as e:
    print(f"CONNECTION FAILED: {type(e).__name__}")
    print(str(e))
    sys.exit(1)
