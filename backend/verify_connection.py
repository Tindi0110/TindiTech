from pymongo import MongoClient
from config import config
import sys

try:
    print(f"Connecting to: {config.MONGODB_URI.split('@')[1]}")
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
    print("Connection Successful!")
except Exception as e:
    print(f"Connection Failed: {e}")
    sys.exit(1)
