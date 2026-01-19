# Tindi Tech Project

A comprehensive E-commerce & ISP Management solution integrating **Flask**, **MongoDB**, **Mikrotik/TP-Link Routers**, and **M-Pesa** payments.

## 🚀 Features

-   **Frontend**: Premium, responsive UI built with vanilla HTML/CSS/JS (no heavy framework overhead).
-   **E-commerce**:
    -   Product catalog with search & filtering.
    -   Guest checkout with M-Pesa STK Push integration.
    -   Admin dashboard for order management (Processing, Refunds, Receipts).
-   **ISP / WiFi Portal**:
    -   Captive portal for Hotspot login.
    -   Voucher & M-Pesa payment login methods.
    -   Real-time integration with Mikrotik/TP-Link routers using `routeros_api` / Controller APIs.
-   **Admin Dashboard**:
    -   Role-Based Access Control (Super Admin vs Staff).
    -   Real-time revenue monitoring (restricted visibility).
    -   User & Message management.

## 🛠️ Setup & Installation

### 1. Prerequisites
-   Python 3.10+
-   MongoDB Atlas (or local instance)
-   Mikrotik Router (optional, for WiFi features)

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the `backend/` directory:
```ini
FLASK_ENV=development
FLASK_SECRET_KEY=your_super_secret_key
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority

# API & Payments
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_PASSKEY=...

# Router Config
ROUTER_TYPE=mikrotik
MIKROTIK_HOST=192.168.88.1
MIKROTIK_USER=admin
MIKROTIK_PASS=
```

### 4. Running the Server
```bash
python main.py
```
Server runs at `http://127.0.0.1:5000`.

### 5. Frontend
Open `frontend/index.html` via a Live Server or access it through the Flask static file serving at `http://127.0.0.1:5000/` (if configured).

## 🔒 Security Notes
-   **Environment Variables**: Never commit `.env` to version control.
-   **Debug Mode**: Ensure `FLASK_ENV=production` when deploying to disable debug mode.
-   **Input Sanitization**: Search inputs are sanitized to prevent NoSQL injection.

## 🚧 Development & Demo Mode
When `FLASK_ENV=development` (default), the following "Mock" behaviors are active for testing without real payments/hardware:
1.  **Auto-Complete Payments**: Viewing an order status will automatically mark it as PAID.
2.  **STK Push Simulation**: If M-Pesa keys are missing, the system simulates a successful STK Push.
3.  **Router Simulation**: Login requests simulate a successful router response.

**To disable these for production, set `FLASK_ENV=production` in `.env`.**

## 📄 License
Tindi Tech Proprietary Software.
