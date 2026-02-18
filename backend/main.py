from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import math
from mikrotik_utils import mikrotik
from tplink_utils import tplink
import bcrypt
import uuid
import datetime
from bson import ObjectId
from config import config
from flask_mail import Mail, Message
from pymongo import MongoClient
import re
import random

# Supabase Utilities
from supabase_utils import create_supabase_user, login_supabase_user, verify_token
import supabase_db
import jwt
import threading
import os
import certifi
from mpesa_utils import initiate_stk_push
from flask_talisman import Talisman


# Serve static files from ../frontend directly at root URL
app = Flask(__name__, static_folder="../frontend", static_url_path="")
# Load configuration from config.py
app.config.from_object(config)

# Security Headers (Talisman)
csp = {
    'default-src': ["'self'", "https://fonts.googleapis.com", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
    'script-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"], # Unsafe-inline needed for some legacy JS
    'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
    'img-src': ["'self'", "data:", "https:", "http:"]
}
Talisman(app, content_security_policy=csp, force_https=False) # Force HTTPS handled by load balancer or env var usually, set False for Dev

# CORS: Restricted
CORS(app, resources={r"/*": {"origins": config.CORS_ORIGINS}}, supports_credentials=True)

# Serve Home.html at root
@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'Home.html')

# ============== RATE LIMITING ==============
# Prevent brute force attacks
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.API_RATE_LIMIT] if config.RATE_LIMIT_ENABLED else [],
    storage_uri="memory://"
)

# Initialize Mail
mail = Mail(app)


# Ensure Indexes (Performance)
def init_db_indexes():
    try:
        users_col.create_index("email", unique=True)
        users_col.create_index("username", unique=True)
        orders_col.create_index("order_id", unique=True)
        # print("[DB] Indexes ensured for high performance")
    except Exception as e:
        if config.DEBUG:
            print(f"[DB] Index warning: {e}")


# Run indexing trigger moved to after DB init

# ============== DATABASE CONNECTION ==============
# Using environment variables for security
client = MongoClient(config.MONGODB_URI, tlsCAFile=certifi.where())
# --- Database & Collections ---
db = client["TindiTech"]
users_col = db["users"]
orders_col = db["orders"]
products_col = db["products"]
services_col = db["services"]  # For service listings
messages_col = db["messages"]  # For contact form submissions
quotes_col = db["quotes"]  # For quote requests
wifi_sessions_col = db["wifi_sessions"]  # For active Wi-Fi users
vouchers_col = db["vouchers"]  # For generated vouchers

# Run indexing on startup (in separate thread to not block)
threading.Thread(target=init_db_indexes).start()

# --- ISP CONSTANTS ---

WIFI_PLANS = {
    "1h": {"duration": 1, "price": 20, "name": "1 Hour Access"},
    "2h": {"duration": 2, "price": 30, "name": "2 Hours Access"},
    "3h": {"duration": 3, "price": 40, "name": "3 Hours Access"},
    "6h": {"duration": 6, "price": 70, "name": "6 Hours Access"},
    "12h": {"duration": 12, "price": 100, "name": "12 Hours Access"},
    "24h": {"duration": 24, "price": 150, "name": "24 Hours Access"},
    "1w": {"duration": 168, "price": 800, "name": "1 Week Access"},
    "1m": {"duration": 720, "price": 2500, "name": "1 Month Access"}  # 30 days
}


# --- Helpers ---

def authorize_router_user(code, mac_address, duration_hours=1):
    """Dispatch authorization to the configured router (MikroTik or TP-Link)."""
    router_type = config.ROUTER_TYPE

    if router_type == 'mikrotik':
        # MikroTik Logic (User/Pass = Code)
        # Duration is handled by User Profile in Router or Backend Heartbeat
        return mikrotik.add_hotspot_user(code, code)

    elif router_type == 'tplink':
        # TP-Link Logic (Authorize MAC)
        # Note: TP-Link relies on MAC address, not code-based login for Controller API usually
        if not mac_address or mac_address == "00:00:00:00:00:00":
            return False, "MAC Address required for TP-Link"

        duration_minutes = int(duration_hours * 60)
        return tplink.authorize_client(mac_address, duration_minutes)

    return False, "Unknown Router Type"


def hash_password(plain_text_password: str) -> bytes:
    return bcrypt.hashpw(plain_text_password.encode("utf-8"), bcrypt.gensalt())


def check_password(plain_text_password: str, hashed: bytes) -> bool:
    if isinstance(hashed, str): hashed = hashed.encode("utf-8")  # Safety fix
    return bcrypt.checkpw(plain_text_password.encode("utf-8"), hashed)


def generate_token(username: str) -> str:
    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config.TOKEN_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def get_token_expiration():
    """Calculate token expiration time based on config."""
    return datetime.datetime.now() + datetime.timedelta(hours=config.TOKEN_EXPIRATION_HOURS)


def is_token_valid(user: dict) -> bool:
    """Check if user's token is still valid (not expired)."""
    if not user.get("token"):
        return False

    expiration = user.get("token_expiration")
    if not expiration:
        # Old tokens without expiration - consider invalid for security
        return False

    return datetime.datetime.now() < expiration


def normalize_phone(phone: str) -> str:
    """Strip all non-numeric characters from a phone number for consistent matching."""
    if not phone: return ""
    return re.sub(r"\D", "", str(phone))


def json_serializer(data):
    """Helper to convert PyMongo objects (like ObjectId, datetime) to JSON serializable format."""
    if isinstance(data, list):
        return [json_serializer(i) for i in data]
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if isinstance(v, ObjectId):
                new_data[k] = str(v)
            elif isinstance(v, datetime.datetime):
                new_data[k] = v.isoformat()
            elif isinstance(v, dict) or isinstance(v, list):
                new_data[k] = json_serializer(v)
            else:
                new_data[k] = v
        return new_data
    return data


def generate_otp():
    """Generate a 6-digit OTP."""
    return ''.join(random.choices('0123456789', k=6))


def send_sms_mock(phone, message):
    """Mock SMS sender - logs to console for dev/testing if DEBUG enabled."""
    if config.DEBUG:
        print(f"\n[MOCK SMS] To: {phone}")
        print(f"[MOCK SMS] Message: {message}\n")
    return True


def send_async_email(subject, recipient, body):
    """Send email asynchronously in background thread to prevent blocking."""
    def _send():
        try:
            with app.app_context():  # Required for Flask-Mail in threads
                msg = Message(subject, recipients=[recipient])
                msg.body = body
                mail.send(msg)
                if config.DEBUG:
                    print(f"[MAIL] Sent: {subject} to {recipient}")
        except Exception as e:
            if config.DEBUG:
                print(f"[MAIL] Failed to send {subject} to {recipient}: {e}")
    
    # Start thread and return immediately
    thread = threading.Thread(target=_send)
    thread.daemon = True  # Don't block app shutdown
    thread.start()


# --- PAGINATION HELPER ---
def get_pagination_params():
    page = request.args.get("page", type=int)
    limit = request.args.get("limit", default=10, type=int)
    search = request.args.get("search", "").strip()
    return page, limit, search


def get_paginated_response(collection, query, sort_key="created_at", sort_order=-1):
    page, limit, search = get_pagination_params()

    # Get Total Count
    total = collection.count_documents(query)

    cursor = collection.find(query).sort(sort_key, sort_order)

    if page:
        cursor = cursor.skip((page - 1) * limit).limit(limit)
        items = list(cursor)
        return {
            "items": json_serializer(items),
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        }
    else:
        # Backward compatibility: return list directly
        return json_serializer(list(cursor))


# ================= AUTHENTICATION =================
@app.route("/register", methods=["POST"])
@limiter.limit(config.LOGIN_RATE_LIMIT)
def register():
    data = request.get_json() or {}
    required = ["fname", "lname", "email", "phone", "username", "password"]
    if not all(k in data and data[k] for k in required):
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    username = data["username"].strip().lower()
    email = data["email"].strip().lower()
    if users_col.find_one({"username": username}):
        return jsonify({"success": False, "error": "Username already exists"}), 400
    if users_col.find_one({"email": email}):
        return jsonify({"success": False, "error": "Email already registered"}), 400
    # Role Assignment Logic (using secure environment variables)
    admin_code = data.get("admin_code", "").strip()
    role = "customer"  # Default

    if admin_code and admin_code == config.SUPER_ADMIN_CODE:
        role = "super_admin"
    elif admin_code and admin_code == config.ADMIN_CODE:
        role = "admin"
    hashed_password = hash_password(data["password"])
    
    email_otp = generate_otp()
    phone_otp = generate_otp()

    user = {
        "fname": data["fname"],
        "lname": data["lname"],
        "username": username,  # Use lowercase version
        "email": data["email"],
        "phone": data.get("phone", ""),
        "password": hashed_password,
        "role": role,
        "created_at": datetime.datetime.now(),
        "is_email_verified": False,
        "is_phone_verified": False,
        "email_otp": email_otp,
        "phone_otp": phone_otp
    }

    try:
        users_col.insert_one(user)
        
        # Send Email OTP (Async - non-blocking)
        send_async_email(
            "Verify your Email - Tindi Tech",
            data["email"],
            f"Your Email Verification Code is: {email_otp}"
        )

        # Send Phone OTP (Mock)
        if user["phone"]:
            send_sms_mock(user["phone"], f"Your Tindi Tech Verification Code is: {phone_otp}")

        return jsonify({
            "success": True, 
            "message": "Registration successful! Verification required.",
            "verification_required": True,
            "email": user["email"],
            "phone": user["phone"]
        }), 201

    except Exception as e: 
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/login", methods=["POST"])
@limiter.limit(config.LOGIN_RATE_LIMIT)
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    user = users_col.find_one({"username": username})
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    # LOCKOUT CHECK
    if user.get("lockout_until") and datetime.datetime.now() < user["lockout_until"]:
        wait_time = (user["lockout_until"] - datetime.datetime.now()).seconds // 60
        return jsonify({"success": False, "error": f"Account locked. Try again in {wait_time + 1} minutes."}), 429

    try:
        ok = check_password(password, user.get("password"))
    except Exception:
        ok = False

    if not ok:
        # Increment Failed Attempts
        attempts = user.get("failed_login_attempts", 0) + 1
        updates = {"failed_login_attempts": attempts}
        
        # Lockout if > 5 attempts
        if attempts >= 5:
            updates["lockout_until"] = datetime.datetime.now() + datetime.timedelta(minutes=15)
            # Reset attempts on lockout so they have a fresh start after timeout
            updates["failed_login_attempts"] = 0 
            
        users_col.update_one({"_id": user["_id"]}, {"$set": updates})

        msg = "Invalid username or password"
        if attempts >= 5: msg = "Account locked for 15 minutes due to too many failed attempts."
        
        return jsonify({"success": False, "error": msg}), 401
    
    # Reset Failed Attempts on Success
    if user.get("failed_login_attempts", 0) > 0:
        users_col.update_one({"_id": user["_id"]}, {"$set": {"failed_login_attempts": 0, "lockout_until": None}})

    # Check Verification
    # Email is always required, phone only if it exists
    if not user.get("is_email_verified"):
        return jsonify({
            "success": False, 
            "error": "Email not verified", 
            "verification_required": True,
            "email": user.get("email"),
            "phone": user.get("phone")
        }), 403
    
    # Only check phone verification if user has a non-empty phone
    has_phone = user.get("phone") and user.get("phone").strip() != ""
    if has_phone and not user.get("is_phone_verified"):
        return jsonify({
            "success": False, 
            "error": "Phone not verified", 
            "verification_required": True,
            "email": user.get("email"),
            "phone": user.get("phone")
        }), 403

    # Generate token for session with expiration and update last_login
    token = generate_token(username)
    token_expiration = get_token_expiration()

    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "token": token,
            "token_expiration": token_expiration,
            "last_login": datetime.datetime.now()
        }}
    )

    # Return user role to frontend to allow access to admin panel if applicable
    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": {
            "username": user["username"],
            "role": user.get("role", "customer")
        }
    })





@app.route("/logout", methods=["POST"])
def logout():
    """Logout current user."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"success": True})  # Already logged out or invalid token

    # Clear token
    users_col.update_one({"_id": user["_id"]}, {"$set": {"token": None}})
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/verify-session", methods=["POST"])
def verify_session():
    """Verify Supabase session and return user info."""
    data = request.get_json() or {}
    token = data.get("token")
    if not token:
        return jsonify({"success": False, "error": "No token provided"}), 401

    user_res = verify_token(token)
    if not user_res:
        return jsonify({"success": False, "error": "Invalid or expired session"}), 401

    user = user_res.user
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.user_metadata.get("username", user.email),
            "role": user.user_metadata.get("role", "customer")
        }
    })


# --- AUTH HELPER ---
def get_authenticated_user():
    """Get authenticated user from Supabase token."""
    token = request.headers.get("Authorization")
    if not token: return None

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    # Verify with Supabase
    user_res = verify_token(token)
    if not user_res: return None
    
    # Return a dict that mimics the expected user object
    user = user_res.user
    return {
        "id": user.id,
        "email": user.email,
        "username": user.user_metadata.get("username", user.email),
        "role": user.user_metadata.get("role", "customer")
    }


@app.route("/forgot-password", methods=["POST"])
@limiter.limit(config.LOGIN_RATE_LIMIT)
def forgot_password():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()  # Safety
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    user = users_col.find_one({"email": email})
    if not user:
        # Security: Don't reveal if user exists
        return jsonify({"success": True, "message": "If that email exists, a reset link has been sent."})

    # Generate Reset Token
    reset_token = str(uuid.uuid4())
    # Expires in 1 hour
    expiration = datetime.datetime.now() + datetime.timedelta(hours=1)

    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"reset_token": reset_token, "reset_token_expiration": expiration}}
    )

    # Send Email
    email_sent = False
    try:
        reset_link = f"{config.FRONTEND_URL}/reset_password.html?token={reset_token}"

        if config.MAIL_USERNAME:
            msg = Message(
                subject="Password Reset Request - Tindi Tech",
                sender=config.MAIL_DEFAULT_SENDER,
                recipients=[email],
                body=f"Hi {user['fname']},\n\nYou requested to reset your password. Click the link below to reset it:\n\n{reset_link}\n\nIf you did not request this, please ignore this email.\n\nLink expires in 1 hour."
            )
            mail.send(msg)
            if config.DEBUG:
                print(f"[MAIL] Sent reset link to {email}")
            email_sent = True
        else:
            if config.DEBUG:
                print("[MAIL] Mail not configured. Reset Key:", reset_token)

        # DEBUG MODE HELPER
        if config.DEBUG and not email_sent:
            return jsonify({
                "success": True,
                "message": "Debug Mode: Email config missing. Using debug link.",
                "debug_link": reset_link
            })

    except Exception as e:
        if config.DEBUG:
            print(f"[MAIL] Error sending email: {e}")
        if config.DEBUG:
            return jsonify({"success": False, "error": f"Mail Error: {str(e)}"})

    # Production response (Standard)
    return jsonify({"success": True, "message": "If that email exists, a reset link has been sent."})


@app.route("/reset-password", methods=["POST"])
@limiter.limit(config.LOGIN_RATE_LIMIT)
def reset_password():
    data = request.get_json() or {}
    token = str(data.get("token", ""))  # Safety
    new_password = str(data.get("password", ""))

    if not token or not new_password:
        return jsonify({"success": False, "error": "Token and new password required"}), 400

    user = users_col.find_one({"reset_token": token})
    if not user:
        return jsonify({"success": False, "error": "Invalid or expired token"}), 400

    # Check expiration
    expiration = user.get("reset_token_expiration")
    if not expiration or datetime.datetime.now() > expiration:
        return jsonify({"success": False, "error": "Token expired"}), 400

    # Reset Password
    hashed = hash_password(new_password)
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password": hashed,
            "reset_token": None,
            "reset_token_expiration": None,
            "token": None  # Optional: Force logout other sessions
        }}
    )

    return jsonify({"success": True, "message": "Password reset successfully. You can now login."})


@app.route("/users", methods=["GET"])
def get_all_users():
    """Get all users with login status (Admin Only)."""
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    # Search Logic
    _, _, search = get_pagination_params()
    query = {}
    if search:
        # Security: Escape special regex characters to prevent injection/ReDoS
        safe_search = re.escape(search)
        query["$or"] = [
            {"username": {"$regex": safe_search, "$options": "i"}},
            {"email": {"$regex": safe_search, "$options": "i"}},
            {"fname": {"$regex": safe_search, "$options": "i"}},
            {"lname": {"$regex": safe_search, "$options": "i"}}
        ]

    # Return users with password excluded, but include token to check login status
    # Note: We need to handle hiding fields manually or via projection if using helper
    # For simplicity w/ helper, we fetch all then stripe, or use custom query

    # Custom pagination flow because of field projection and 'is_logged_in' logic
    page, limit, _ = get_pagination_params()
    total = users_col.count_documents(query)
    cursor = users_col.find(query, {"password": 0}).sort("created_at", -1)

    if page:
        cursor = cursor.skip((page - 1) * limit).limit(limit)

    users = list(cursor)
    for u in users:
        # Check token validity (expiration) not just existence
        u['is_logged_in'] = is_token_valid(u)

    data = json_serializer(users)

    if page:
        return jsonify({
            "success": True,
            "data": {
                "items": data,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
        })
    return jsonify({"success": True, "data": data})


@app.route("/users/<id>/logout", methods=["POST"])
def force_logout_user(id):
    """Force logout a user by clearing their token (Super Admin Only)."""
    admin = get_authenticated_user()
    if not admin or admin.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        result = users_col.update_one({"_id": ObjectId(id)}, {"$set": {"token": None}})
        if result.matched_count == 0:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True, "message": "User logged out"})
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid ID"}), 400


@app.route("/users/<id>", methods=["DELETE"])
def delete_user(id):
    """Delete a user permanently (Super Admin Only)."""
    admin = get_authenticated_user()
    if not admin or admin.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        # Prevent deleting yourself
        if str(admin["_id"]) == id:
            return jsonify({"success": False, "error": "Cannot delete yourself"}), 400

        # Find user to check role
        user_to_delete = users_col.find_one({"_id": ObjectId(id)})
        if not user_to_delete:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Prevent deleting other super admins
        if user_to_delete.get("role") == "super_admin":
            return jsonify({"success": False, "error": "Cannot delete super admin accounts"}), 403

        # Delete the user
        users_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/verify-account", methods=["POST"])
def verify_account():
    """Verify Email and/or Phone OTPs."""
    data = request.get_json()
    email = data.get("email")
    email_otp_input = data.get("email_otp")
    phone_otp_input = data.get("phone_otp")

    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    updates = {}
    
    # Verify Email
    if email_otp_input:
        if str(user.get("email_otp")) == str(email_otp_input):
            updates["is_email_verified"] = True
            updates["email_otp"] = None # Clear OTP
        else:
            return jsonify({"success": False, "error": "Invalid Email OTP"}), 400

    # Verify Phone (only if phone_otp provided)
    if phone_otp_input:
        if str(user.get("phone_otp")) == str(phone_otp_input):
            updates["is_phone_verified"] = True
            updates["phone_otp"] = None 
        else:
            return jsonify({"success": False, "error": "Invalid Phone OTP"}), 400
    
    # If user has no phone or empty phone, auto-verify phone
    if not user.get("phone") or user.get("phone").strip() == "":
        updates["is_phone_verified"] = True

    if updates:
        users_col.update_one({"_id": user["_id"]}, {"$set": updates})

    # Check updated status
    updated_user = users_col.find_one({"_id": user["_id"]})
    
    # User is verified if email is verified AND (phone is verified OR no phone exists)
    has_phone = updated_user.get("phone") and updated_user.get("phone").strip() != ""
    is_fully_verified = updated_user.get("is_email_verified") and (
        updated_user.get("is_phone_verified") or not has_phone
    )

    # Generate token for auto-login if email verified (phone optional)
    token = None
    if updated_user.get("is_email_verified"):
        token = generate_token(updated_user["username"])
        token_expiration = get_token_expiration()
        users_col.update_one(
            {"_id": updated_user["_id"]},
            {"$set": {
                "token": token,
                "token_expiration": token_expiration
            }}
        )

    response = {
        "success": True, 
        "message": "Verification successful!",
        "is_fully_verified": is_fully_verified
    }
    
    # Include token and user info for auto-login
    if token:
        response["token"] = token
        response["user"] = {
            "username": updated_user["username"],
            "role": updated_user.get("role", "customer")
        }

    return jsonify(response)


@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    """Resend OTPs to unverified users."""
    data = request.get_json()
    email = data.get("email")

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Generate new OTPs if needed
    updates = {}
    email_otp = user.get("email_otp")
    if not user.get("is_email_verified"):
        email_otp = generate_otp()
        updates["email_otp"] = email_otp
    
    phone_otp = user.get("phone_otp")
    if not user.get("is_phone_verified"):
        phone_otp = generate_otp()
        updates["phone_otp"] = phone_otp

    if updates:
        users_col.update_one({"_id": user["_id"]}, {"$set": updates})
        
        if "email_otp" in updates:
            # Send email asynchronously
            send_async_email(
                "New Verification Code - Tindi Tech",
                email,
                f"Your New Email Code is: {email_otp}"
            )
        
        if "phone_otp" in updates and user.get("phone"):
            send_sms_mock(user["phone"], f"Your New Phone Code is: {phone_otp}")

    return jsonify({"success": True, "message": "OTPs resent"})


# ================= PRODUCTS (CRUD) =================
@app.route("/products", methods=["GET"])
def get_products():
    """Get all products (Public + Admin w/ Pagination)."""
    page, limit, search = get_pagination_params()
    query = {}
    if search:
        safe_search = re.escape(search)
        query["name"] = {"$regex": safe_search, "$options": "i"}
        # Optional: search category too
        # query["$or"] = [{"name": ...}, {"category": ...}]

    data = get_paginated_response(products_col, query)
    return jsonify({"success": True, "data": data})


@app.route("/products", methods=["POST"])
def add_product():
    """Add a new product (Admin)."""
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json() or {}
    if not data.get("name") or not data.get("price"):
        return jsonify({"success": False, "error": "Name and Price required"}), 400

    # Validate Image (Base64)
    image = data.get("image", "img/pics/default-product.png")
    if image.startswith("data:"):
        # Simple Magic Byte / MIME check for Base64
        if not re.match(r"^data:image/(png|jpeg|jpg|gif|webp);base64,", image):
             return jsonify({"success": False, "error": "Invalid image format. Allowed: png, jpg, gif, webp"}), 400

    product = {
        "name": data["name"],
        "price": data["price"],
        "description": data.get("description", ""),
        "category": data.get("category", "General"),
        "stock": int(data.get("stock", 0)), # Added Stock
        "image": image,
        "created_at": datetime.datetime.now()
    }
    products_col.insert_one(product)
    return jsonify({"success": True, "message": "Product added"})


@app.route("/products/<id>", methods=["DELETE"])
def delete_product(id):
    """Delete a product by ID (Super Admin Only)."""
    user = get_authenticated_user()
    if not user or user.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        products_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"success": True, "message": "Product deleted"})
    except Exception:
        return jsonify({"success": False, "error": "Invalid ID"}), 400


@app.route("/products/<id>", methods=["PUT"])
def update_product(id):
    """Update a product by ID (Admin)."""
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json() or {}
    update_fields = {}

    if "name" in data: update_fields["name"] = data["name"]
    if "price" in data: update_fields["price"] = data["price"]
    if "description" in data: update_fields["description"] = data["description"]
    if "category" in data: update_fields["category"] = data["category"]
    if "image" in data: update_fields["image"] = data["image"]
    if "stock" in data: update_fields["stock"] = int(data["stock"]) # Added Stock

    if not update_fields:
        return jsonify({"success": False, "error": "No fields to update"}), 400
    try:
        products_col.update_one({"_id": ObjectId(id)}, {"$set": update_fields})
        return jsonify({"success": True, "message": "Product updated"})
    except Exception:
        return jsonify({"success": False, "error": "Invalid ID"}), 400


# ================= DELETION ENDPOINTS (SUPER ADMIN) =================



@app.route("/messages/<id>", methods=["DELETE"])
def delete_message(id):
    """Delete a message (Super Admin Only)."""
    user = get_authenticated_user()
    if not user or user.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        messages_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"success": True, "message": "Message deleted"})
    except Exception:
        return jsonify({"success": False, "error": "Invalid ID"}), 400


@app.route("/quotes/<id>", methods=["DELETE"])
def delete_quote(id):
    """Delete a quote (Super Admin Only)."""
    user = get_authenticated_user()
    if not user or user.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        quotes_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"success": True, "message": "Quote deleted"})
    except Exception:
        return jsonify({"success": False, "error": "Invalid ID"}), 400


# ================= ORDERS =================
@app.route("/orders", methods=["GET"])
def get_orders():
    """Get all orders (Admin)."""
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    _, _, search = get_pagination_params()
    query = {}
    if search:
        query["$or"] = [
            {"order_id": {"$regex": search, "$options": "i"}},
            {"customer.name": {"$regex": search, "$options": "i"}},
            {"customer.phone": {"$regex": search, "$options": "i"}}
        ]

    data = get_paginated_response(orders_col, query)
    return jsonify({"success": True, "data": data})


@app.route("/create-order", methods=["POST"])
def create_order():
    try:
        data = request.get_json() or {}
        if not data.get("items") or not data.get("customer"):
            return jsonify({"success": False, "error": "Invalid order data"}), 400

        items = data["items"]
        
        # --- STOCK MANAGEMENT: CHECK & DEDUCT ---
        stock_deductions = [] # To track what we need to deduct
        
        # 1. Validation Pass
        for item in items:
            name = item.get("name")
            qty = int(item.get("quantity", 1))
            
            product = products_col.find_one({"name": name})
            if not product:
                return jsonify({"success": False, "error": f"Product '{name}' no longer exists"}), 400
            
            current_stock = int(product.get("stock", 0))
            if current_stock < qty:
                return jsonify({"success": False, "error": f"Insufficient stock for '{name}'. Only {current_stock} left."}), 400
                
            stock_deductions.append((product["_id"], qty))

        # 2. Deduction Pass (with Rollback capability)
        deducted_log = []
        try:
            for pid, qty in stock_deductions:
                # Atomic update: only deduct if stock >= qty
                res = products_col.update_one(
                    {"_id": pid, "stock": {"$gte": qty}},
                    {"$inc": {"stock": -qty}}
                )
                if res.matched_count == 0:
                    raise Exception(f"Stock changed during processing")
                deducted_log.append((pid, qty))
        except Exception as e:
            # Rollback previous deductions if any failure occurs
            for pid, qty in deducted_log:
                products_col.update_one({"_id": pid}, {"$inc": {"stock": qty}})
            return jsonify({"success": False, "error": f"Stock error: {str(e)}"}), 400

        # --- USER ACCOUNT LINKING ---
        token = request.headers.get("Authorization")
        username = None
        if token:
            user = users_col.find_one({"token": token})
            if user:
                username = user.get("username")
        
        phone_raw = data.get("customer", {}).get("phone", "")
        phone_norm = normalize_phone(phone_raw)

        order_id = str(uuid.uuid4())
        order = {
            "order_id": order_id,
            "username": username, # Linked account if logged in
            "phone_normalized": phone_norm, # For smart matching
            "created_at": datetime.datetime.now(),
            "customer": data["customer"],
            "items": data["items"],
            "subtotal": data.get("sub"),
            "tax": data.get("tax"),
            "shipping": data.get("shipping"),
            "total": data.get("total"),
            "status": "pending",
            "payment": {"status": "pending", "method": "mpesa"}
        }
        orders_col.insert_one(order)
        return jsonify({"success": True, "message": "Order created", "orderId": order_id})
    except Exception as e:
        if config.DEBUG:
            print(f"Error creating order: {e}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/stk-push", methods=["POST"])
def stk_push():
    # Allow public access for guest checkout
    # user = get_authenticated_user()
    # if not user: return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}
    phone = data.get("phone")
    amount = data.get("amount")
    order_id = data.get("orderId")

    # If order_id provided, fetch amount from DB (Secure)
    if order_id:
        order = orders_col.find_one({"order_id": order_id})
        if order:
            amount = order.get("total")
        else:
             return jsonify({"success": False, "error": "Order not found"}), 404

    if not phone or not amount:
        return jsonify({"success": False, "error": "Phone and Amount required"}), 400

    # Call M-Pesa Utility
    result = initiate_stk_push(phone, amount)

    if result["success"]:
        # Update order with checkout ID if available
        if order_id:
            orders_col.update_one({"order_id": order_id}, 
                {"$set": {"payment.checkout_id": result.get("checkout_request_id")}})
        
        return jsonify({"success": True, "message": "STK Push sent to phone",
                        "checkout_request_id": result.get("checkout_request_id")})
    else:
        # In development without keys, this will fail. We handle it gracefully.
        if config.DEBUG:
            # Fallback for demo if keys missing
            return jsonify({"success": True, "message": "Demo: STK Push Simulaton", "checkout_request_id": f"demo-{uuid.uuid4()}"})
        return jsonify(result), 400


@app.route("/api/mpesa/callback", methods=["POST"])
def mpesa_callback():
    """
    Handle M-Pesa IPN (Instant Payment Notification)
    Safaricom sends a POST request here when a transaction completes or fails.
    """
    data = request.get_json() or {}
    if config.DEBUG:
        print(f"[M-PESA] Callback Received: {data}")
    
    # Check if Body exists
    body = data.get("Body", {})
    stkCallback = body.get("stkCallback", {})
    
    checkout_id = stkCallback.get("CheckoutRequestID")
    result_code = stkCallback.get("ResultCode")
    result_desc = stkCallback.get("ResultDesc")
    
    if not checkout_id:
        return jsonify({"success": False, "message": "Invalid Callback payload"}), 400

    if config.DEBUG:
        print(f"[M-PESA] Processing Callback. ID: {checkout_id}, Code: {result_code}, Desc: {result_desc}")

    # Determine status
    payment_status = "failed"
    order_status = "canceled" # Default if failed
    
    # ResultCode 0 means SUCCESS
    if result_code == 0:
        payment_status = "paid"
        order_status = "processing"
        
        # Extract metadata (Amount, Receipt Check, etc.)
        meta_items = stkCallback.get("CallbackMetadata", {}).get("Item", [])
        receipt_number = next((item.get("Value") for item in meta_items if item.get("Name") == "MpesaReceiptNumber"), None)
        phone = next((item.get("Value") for item in meta_items if item.get("Name") == "PhoneNumber"), None)
        amount_paid = next((item.get("Value") for item in meta_items if item.get("Name") == "Amount"), None)
        
        if config.DEBUG:
            print(f"[M-PESA] Success! Receipt: {receipt_number}, Amount: {amount_paid}")
        
        # Update details map
        payment_details = {
            "payment.status": payment_status,
            "status": order_status,
            "payment.receipt_number": receipt_number,
            "payment.phone": phone,
            "payment.paid_at": datetime.datetime.now()
        }
    else:
        # User Cancelled or Failed
        if config.DEBUG:
            print(f"[M-PESA] Payment Failed/Cancelled.")
        payment_details = {
            "payment.status": "failed",
            "payment.failure_reason": result_desc
        }
        # Note: We might NOT want to auto-cancel the order immediately, 
        # just mark payment as failed so they can retry. 
        # But user asked for logic where it's only paid if actually paid.
        
    # UPDATE ORDER
    # We search by 'payment.checkout_id' which we saved during stk_push
    result = orders_col.update_one(
        {"payment.checkout_id": checkout_id},
        {"$set": payment_details}
    )
    
    if result.matched_count > 0:
        if config.DEBUG: print(f"[M-PESA] Order updated via callback.")
    else:
        # Could be a Wi-Fi Session?
        if config.DEBUG: print(f"[M-PESA] No order found for CheckoutID {checkout_id}. Checking Wi-Fi sessions...")
        # (Optional: Add logic to update Wi-Fi session if that's also using this callback)
        wifi_result = wifi_sessions_col.update_one(
             {"checkout_request_id": checkout_id},
             {"$set": {
                 "status": "paid" if result_code == 0 else "failed",
                 "mpesa_code": next((item.get("Value") for item in meta_items if item.get("Name") == "MpesaReceiptNumber"), "FAILED") if result_code == 0 else None,
                 "paid_at": datetime.datetime.now()
             }}
        )
        if wifi_result.matched_count > 0:
             if config.DEBUG: print("[M-PESA] Wi-Fi Session updated.")
        else:
             if config.DEBUG: print("[M-PESA] No matching record found for callback.")

    return jsonify({"success": True})





@app.route("/order/<order_id>", methods=["GET"])
def get_order_status(order_id):
    order = orders_col.find_one({"order_id": order_id})
    if not order: return jsonify({"success": False, "error": "Not found"}), 404

    # Logic for auto-completing payment has been removed to ensure strict payment verification.
    # The status will now only update via M-Pesa Callback or manual check.


    return jsonify({
        "success": True,
        "order": json_serializer(order)
    })


@app.route("/orders/<order_id>", methods=["PATCH"])
def update_order_status(order_id):
    """Admin update order status."""
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ["pending", "processing", "completed", "canceled", "refunded", "refund_requested"]:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    # Fetch existing order to check previous status for Stock Management
    existing_order = orders_col.find_one({"order_id": order_id})
    if not existing_order:
        return jsonify({"success": False, "error": "Order not found"}), 404
        
    old_status = existing_order.get("status")

    update_doc = {"status": new_status}
    if new_status == "canceled":
        update_doc["payment.status"] = "failed"  # Optional: ensure payment marked failed

    result = orders_col.update_one({"order_id": order_id}, {"$set": update_doc})
    if result.matched_count == 0:
        return jsonify({"success": False, "error": "Order not found"}), 404

    # --- STOCK RESTOCKING LOGIC ---
    # If moving TO canceled/refunded FROM a valid state, RESTOCK items
    failed_states = ["canceled", "refunded", "failed"]
    if new_status in failed_states and old_status not in failed_states:
        for item in existing_order.get("items", []):
            name = item.get("name")
            qty = int(item.get("quantity", 0))
            if name and qty > 0:
                products_col.update_one({"name": name}, {"$inc": {"stock": qty}})

    return jsonify({"success": True, "message": "Order status updated"})


@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    """Admin Delete Order Permanently"""
    user = get_authenticated_user()
    if not user or user["role"] not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    result = orders_col.delete_one({"order_id": order_id})
    if result.deleted_count == 0:
        return jsonify({"success": False, "error": "Order not found"}), 404

    return jsonify({"success": True, "message": "Order deleted permanently"})


@app.route("/orders/<order_id>/details", methods=["GET"])
def get_order_details(order_id):
    """Get full order details for receipt (User or Admin)."""
    user = get_authenticated_user()
    if not user: return jsonify({"success": False, "error": "Unauthorized"}), 401

    order = orders_col.find_one({"order_id": order_id})
    if not order: return jsonify({"success": False, "error": "Not found"}), 404

    # RBAC: Allow if Admin OR if Order Owner
    is_admin = user.get("role") in ["admin", "super_admin"]
    is_owner = (order["customer"].get("email") == user["email"]) or (order["customer"].get("phone") == user["phone"])

    if not is_admin and not is_owner:
        return jsonify({"success": False, "error": "Forbidden"}), 403

    return jsonify({"success": True, "data": json_serializer(order)})


# ================= USER ORDERS =================
@app.route("/my-orders", methods=["GET"])
def get_user_orders():
    token = request.headers.get("Authorization")
    if not token: return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = users_col.find_one({"token": token})
    if not user: return jsonify({"success": False, "error": "Invalid token"}), 401

    # Find orders by username, email or normalized phone
    phone_norm = normalize_phone(user.get("phone", ""))
    
    orders = list(orders_col.find({
        "$or": [
            {"username": user.get("username")},
            {"customer.email": user.get("email")},
            {"phone_normalized": phone_norm},
            {"customer.phone": user.get("phone")} # Fallback for old orders
        ]
    }).sort("created_at", -1))

    return jsonify({"success": True, "data": json_serializer(orders)})


@app.route("/my-orders/<order_id>/cancel", methods=["PATCH"])
def cancel_user_order(order_id):
    token = request.headers.get("Authorization")
    if not token: return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = users_col.find_one({"token": token})
    if not user: return jsonify({"success": False, "error": "Invalid token"}), 401

    # Must check ownership
    order = orders_col.find_one({"order_id": order_id})
    if not order: return jsonify({"success": False, "error": "Order not found"}), 404

    # Verify ownership
    if order["customer"].get("email") != user["email"] and order["customer"].get("phone") != user["phone"]:
        return jsonify({"success": False, "error": "Not your order"}), 403

    if order.get("status") not in ["pending", "processing"]:
        return jsonify({"success": False, "error": "Can only cancel pending or processing orders"}), 400

    # Soft Delete: Update status instead of removing
    orders_col.update_one({"order_id": order_id}, {"$set": {"status": "canceled"}})

    # --- STOCK RESTOCKING (User Action) ---
    for item in order.get("items", []):
        name = item.get("name")
        qty = int(item.get("quantity", 0))
        if name and qty > 0:
            products_col.update_one({"name": name}, {"$inc": {"stock": qty}})

    return jsonify({"success": True, "message": "Order canceled"})


@app.route("/my-orders/<order_id>/refund-request", methods=["POST"])
def request_refund(order_id):
    user = get_authenticated_user()
    if not user: return jsonify({"success": False, "error": "Unauthorized"}), 401

    order = orders_col.find_one({"order_id": order_id})
    if not order: return jsonify({"success": False, "error": "Not found"}), 404

    # Ownership
    if order["customer"].get("email") != user["email"] and order["customer"].get("phone") != user["phone"]:
        return jsonify({"success": False, "error": "Not your order"}), 403

    if order.get("status") != "completed":
        return jsonify({"success": False, "error": "Only completed orders can be refunded"}), 400

    orders_col.update_one({"order_id": order_id}, {"$set": {"status": "refund_requested"}})
    return jsonify({"success": True, "message": "Refund requested successfully"})


@app.route("/orders/<order_id>/refund-action", methods=["POST"])
def admin_refund_action(order_id):
    """Admin approve/decline refund."""
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json() or {}
    action = data.get("action")

    if action not in ["approve", "decline", "reject"]:
        return jsonify({"success": False, "error": "Invalid action"}), 400

    new_status = "refunded" if action == "approve" else "completed"

    result = orders_col.update_one({"order_id": order_id}, {"$set": {"status": new_status}})
    if result.matched_count == 0:
        return jsonify({"success": False, "error": "Order not found"}), 404

    # --- STOCK RESTOCKING (Refund Approved) ---
    if new_status == "refunded":
         # Fetch order to get items
        order = orders_col.find_one({"order_id": order_id})
        if order:
            for item in order.get("items", []):
                name = item.get("name")
                qty = int(item.get("quantity", 0))
                if name and qty > 0:
                    products_col.update_one({"name": name}, {"$inc": {"stock": qty}})

    return jsonify({"success": True, "message": f"Refund {action}d"})


# ================= MESSAGES & QUOTES =================
@app.route("/contact", methods=["POST"])
def contact_submit():
    data = request.get_json() or {}
    msg = {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),  # Added Phone
        "subject": data.get("subject"),
        "message": data.get("message"),
        "created_at": datetime.datetime.now()
    }
    messages_col.insert_one(msg)
    return jsonify({"success": True, "message": "Message sent"})



@app.route("/auto-login", methods=["POST"])
def auto_login():
    data = request.get_json() or {}
    token = data.get("token")
    if not token: 
        return jsonify({"success": False, "error": "Token required"}), 400
        
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        user = users_col.find_one({"username": payload["username"]})
        if not user:
             return jsonify({"success": False, "error": "User not found"}), 404

        return jsonify({
            "success": True, 
            "user": {
                "username": user["username"],
                "role": user.get("role", "customer"),
                "email": user.get("email")
            }
        })
    except jwt.ExpiredSignatureError:
        return jsonify({"success": False, "error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "error": "Invalid token"}), 401
    except Exception as e:
        if config.DEBUG:
            print(f"Error: {e}")
        return jsonify({"success": False, "error": "Internal Error"}), 500

@app.route("/quote", methods=["POST"])
def quote_submit():
    data = request.get_json() or {}
    quote = {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),  # Added Phone
        "details": data.get("details"),
        "created_at": datetime.datetime.now()
    }
    quotes_col.insert_one(quote)
    return jsonify({"success": True, "message": "Quote request received"})


@app.route("/messages", methods=["GET"])
def get_messages():
    _, _, search = get_pagination_params()
    query = {}
    if search:
        safe_search = re.escape(search)
        query["$or"] = [
            {"name": {"$regex": safe_search, "$options": "i"}},
            {"email": {"$regex": safe_search, "$options": "i"}},
            {"subject": {"$regex": safe_search, "$options": "i"}}
        ]
    data = get_paginated_response(messages_col, query)
    return jsonify({"success": True, "data": data})


@app.route("/quotes", methods=["GET"])
def get_quotes():
    _, _, search = get_pagination_params()
    query = {}
    if search:
        safe_search = re.escape(search)
        query["$or"] = [
            {"name": {"$regex": safe_search, "$options": "i"}},
            {"email": {"$regex": safe_search, "$options": "i"}},
            {"details": {"$regex": safe_search, "$options": "i"}}
        ]
    data = get_paginated_response(quotes_col, query)
    return jsonify({"success": True, "data": data})



# ================= ISP / WIFI BILLING =================

@app.route("/wifi/plans", methods=["GET"])
def get_wifi_plans():
    """Return hardcoded/dynamic Wi-Fi plans."""
    return jsonify({"success": True, "plans": WIFI_PLANS})


@app.route("/wifi/pay", methods=["POST"])
def wifi_pay():
    """Initiate M-Pesa Payment for Wi-Fi (Persistent)."""
    data = request.get_json() or {}
    phone = data.get("phone")
    plan_id = data.get("plan_id")
    mac_address = data.get("mac_address")

    if not phone or not plan_id or plan_id not in WIFI_PLANS:
        return jsonify({"success": False, "error": "Invalid phone or plan"}), 400

    plan = WIFI_PLANS[plan_id]
    amount = plan["price"]

    # 1. Initiate STK Push
    result = initiate_stk_push(phone, amount)

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "Failed to initiate payment")}), 400

    # 2. Store Session in MongoDB (Status: pending_payment)
    session_id = str(uuid.uuid4())
    wifi_sessions_col.insert_one({
        "session_id": session_id,
        "phone": phone,
        "plan_id": plan_id,
        "amount": amount,
        "status": "pending_payment", 
        "created_at": datetime.datetime.now(),
        "checkout_request_id": result.get("checkout_request_id"),
        "mpesa_code": None,
        "type": "mpesa",
        "mac_address": mac_address,
        "start_time": None,
        "expiry_time": None
    })

    return jsonify({
        "success": True,
        "message": "STK Push Sent. Enter M-Pesa Code to login.",
        "checkout_request_id": result.get("checkout_request_id")
    })


@app.route("/wifi/status/<checkout_id>", methods=["GET"])
def wifi_check_status(checkout_id):
    """Check payment status from MongoDB. Demo Only: Auto-complete."""
    session = wifi_sessions_col.find_one({"checkout_request_id": checkout_id})
    if not session:
        return jsonify({"success": False, "status": "not_found"}), 404

    status = session.get("status")

    # --- DEMO AUTO-COMPLETION LOGIC ---
    # logic for auto-completing payment has been removed.
    # Status updates only via callback.

    return jsonify({
        "success": True,
        "status": status,
        "code": session.get("mpesa_code"),
        "router_type": config.ROUTER_TYPE
    })


@app.route("/wifi/login", methods=["POST"])
def wifi_login():
    """Login with M-Pesa Code or Voucher (MongoDB Verified)."""
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    mac_address = data.get("mac_address", "00:00:00:00:00:00")

    if not code: return jsonify({"success": False, "error": "Code required"}), 400

    now = datetime.datetime.now()

    # 1. CHECK VOUCHERS
    voucher = vouchers_col.find_one({"code": code})
    if voucher:
        if voucher.get("status") == "used":
            # Re-login allowed if consistent MAC and not expired? 
            # Simplified: Once used, it becomes a session. Check sessions instead.
            pass 
        else:
             # Activate new voucher
            duration = voucher.get("duration_hours", 1)
            expiry = now + datetime.timedelta(hours=duration)
            
            # Create Session
            wifi_sessions_col.insert_one({
                "session_id": str(uuid.uuid4()),
                "type": "voucher",
                "code": code,
                "mac_address": mac_address,
                "start_time": now,
                "expiry_time": expiry,
                "last_heartbeat": now,
                "status": "active",
                "duration_hours": duration
            })
            # Mark Used
            vouchers_col.update_one({"_id": voucher["_id"]}, {"$set": {"status": "used", "used_at": now}})
            
            authorize_router_user(code, mac_address, duration)
            return jsonify({
                "success": True, 
                "message": "Voucher Activated", 
                "router_type": config.ROUTER_TYPE,
                "expiry": expiry.isoformat()
            })

    # 2. CHECK SESSIONS (M-Pesa or Used Voucher)
    # Search by mpesa_code OR voucher code
    session = wifi_sessions_col.find_one({"$or": [{"mpesa_code": code}, {"code": code}]})
    
    if not session:
         return jsonify({"success": False, "error": "Invalid Code"}), 401

    if session.get("status") == "pending_payment":
        return jsonify({"success": False, "error": "Payment not completed"}), 401

    # If first time login for M-Pesa
    if session.get("status") == "paid":
        plan_id = session.get("plan_id")
        plan = WIFI_PLANS.get(plan_id)
        duration = plan["duration"] if plan else 1
        expiry = now + datetime.timedelta(hours=duration)

        wifi_sessions_col.update_one({"_id": session["_id"]}, {
            "$set": {
                "status": "active",
                "start_time": now,
                "expiry_time": expiry,
                "last_heartbeat": now,
                "mac_address": mac_address
            }
        })
        authorize_router_user(code, mac_address, duration)
        return jsonify({
            "success": True, 
            "message": "Login Successful", 
            "router_type": config.ROUTER_TYPE,
            "expiry": expiry.isoformat()
        })

    # If already active (Re-login/Reconnect)
    if session.get("status") == "active":
        if session.get("expiry_time") and session["expiry_time"] < now:
            return jsonify({"success": False, "error": "Plan Expired"}), 403
        
        # Determine duration remaining
        remaining_seconds = (session["expiry_time"] - now).total_seconds()
        remaining_hours = remaining_seconds / 3600
        
        # update heartbeat
        wifi_sessions_col.update_one({"_id": session["_id"]}, {"$set": {"last_heartbeat": now, "mac_address": mac_address}})
        
        authorize_router_user(code, mac_address, remaining_hours)
        return jsonify({
            "success": True, 
            "message": "Welcome Back", 
            "router_type": config.ROUTER_TYPE,
            "expiry": session["expiry_time"].isoformat()
        })

    return jsonify({"success": False, "error": "Unknown Error"}), 500


@app.route("/wifi/heartbeat", methods=["POST"])
def wifi_heartbeat():
    data = request.get_json() or {}
    code = data.get("code")
    if code:
        wifi_sessions_col.update_one(
            {"$or": [{"mpesa_code": code}, {"code": code}]},
            {"$set": {"last_heartbeat": datetime.datetime.now()}}
        )
    return jsonify({"success": True})


@app.route("/wifi/claim-compensation", methods=["POST"])
def claim_compensation():
    """Check for downtime and issue voucher if needed."""
    return jsonify({"success": False, "message": "No outages detected."})


# --- ADMIN ISP MANAGER API ---

@app.route("/admin/wifi-stats", methods=["GET"])
def get_wifi_stats():
    admin = get_authenticated_user()
    if not admin or admin.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    active_count = wifi_sessions_col.count_documents({"status": "active", "expiry_time": {"$gt": datetime.datetime.now()}})
    
    # Revenue aggregation
    pipeline = [
        {"$match": {"status": {"$in": ["active", "expired", "paid"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    res = list(wifi_sessions_col.aggregate(pipeline))
    revenue = res[0]["total"] if res else 0

    # Privacy: Hide revenue from regular admins
    if admin.get("role") != "super_admin":
        revenue = None

    return jsonify({"success": True, "active_users": active_count, "total_revenue": revenue})


@app.route("/admin/wifi-sessions", methods=["GET"])
def get_wifi_sessions():
    admin = get_authenticated_user()
    if not admin: return jsonify({"success": False}), 403
    
    sessions = list(wifi_sessions_col.find().sort("created_at", -1).limit(50))
    return jsonify({"success": True, "data": json_serializer(sessions)})


@app.route("/admin/wifi-sessions/<id>", methods=["DELETE"])
def delete_wifi_session(id):
    admin = get_authenticated_user()
    if not admin or admin.get("role") != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    wifi_sessions_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"success": True, "message": "Deleted"})


@app.route("/admin/generate-voucher", methods=["POST"])
def admin_generate_voucher():
    admin = get_authenticated_user()
    if not admin: return jsonify({"success": False}), 403
    
    data = request.get_json() or {}
    hours = int(data.get("hours", 1))
    code = "VOU-" + str(uuid.uuid4())[:8].upper()
    
    vouchers_col.insert_one({
        "code": code,
        "duration_hours": hours,
        "status": "active",
        "created_at": datetime.datetime.now(),
        "created_by": admin.get("username")
    })
    return jsonify({"success": True, "code": code})


# ================= DASHBOARD STATS =================
@app.route("/admin/stats/charts", methods=["GET"])
def get_admin_charts_data():
    admin = get_authenticated_user()
    if not admin or admin.get("role") not in ["admin", "super_admin"]:
        # Allow if validation disabled for dev, else 403. Keeping strict for now.
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    # 1. Order Status Distribution (Pie Chart)
    pipeline_status = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_data = list(orders_col.aggregate(pipeline_status))
    # Format: {"pending": 5, "completed": 10, ...}
    status_counts = {item["_id"]: item["count"] for item in status_data}

    # 2. Revenue Over Last 7 Days (Line Chart)
    # Get last 7 days dates
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=6)
    
    pipeline_revenue = [
        {
            "$match": {
                "created_at": {"$gte": start_date},
                "status": {"$in": ["completed", "processing", "paid"]} # Count revenue from valid orders
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"}
                },
                "daily_total": {"$sum": "$total"}
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
    ]
    
    revenue_data = list(orders_col.aggregate(pipeline_revenue))
    
    # Fill in missing days with 0
    final_revenue = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        # Find match
        day_total = 0
        for r in revenue_data:
            d = r["_id"]
            r_date = f"{d['year']}-{d['month']:02d}-{d['day']:02d}"
            if r_date == date_str:
                day_total = r["daily_total"]
                break
        
        final_revenue.append({"date": date_str, "total": day_total})
        current += datetime.timedelta(days=1)

    return jsonify({
        "success": True, 
        "status_distribution": status_counts,
        "revenue_trend": final_revenue
    })


@app.route("/admin/stats", methods=["GET"])
def get_admin_stats():
    # Admin only check
    user = get_authenticated_user()
    if not user or user.get("role") not in ["admin", "super_admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    total_revenue = 0
    pending_revenue = 0

    orders = list(orders_col.find({}))
    for o in orders:
        status = o.get("status", "pending")
        amount = o.get("total", 0)
        if status == "completed":
            total_revenue += amount
        elif status in ["pending", "processing"]:
            pending_revenue += amount

    total_orders = len(orders)
    total_products = products_col.count_documents({})
    total_users = users_col.count_documents({})

    # Privacy: Hide revenue from regular admins
    if user.get("role") != "super_admin":
        total_revenue = None
        pending_revenue = None

    return jsonify({
        "success": True,
        "revenue": total_revenue,
        "pending_revenue": pending_revenue,
        "orders": total_orders,
        "products": total_products,
        "users": total_users
    })


if __name__ == "__main__":
    # Only enable debug in development, NEVER in production
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)

