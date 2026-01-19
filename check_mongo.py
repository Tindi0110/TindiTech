
from pymongo import MongoClient
import sys

try:
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    client.server_info() # Force connection
    print("SUCCESS: Local MongoDB is running.")
except Exception as e:
    print(f"FAILURE: Could not connect to local MongoDB. Error: {e}")
    sys.exit(1)
