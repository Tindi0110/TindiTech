import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load env vars explicitly
load_dotenv()

SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
PORT = int(os.getenv('MAIL_PORT', 587))
USERNAME = os.getenv('MAIL_USERNAME')
PASSWORD = os.getenv('MAIL_PASSWORD')

print(f"Testing Email with:")
print(f"Server: {SERVER}:{PORT}")
print(f"User: {USERNAME}")
print(f"Pass: {'*' * len(PASSWORD) if PASSWORD else 'NONE'}")

try:
    print("Connecting...")
    server = smtplib.SMTP(SERVER, PORT)
    server.set_debuglevel(1)  # Show communication
    print("Starting TLS...")
    server.starttls()
    print("Logging in...")
    server.login(USERNAME, PASSWORD)
    print("LOGIN SUCCESSFUL!")
    server.quit()
except Exception as e:
    print(f"\nLOGIN FAILED: {e}")
