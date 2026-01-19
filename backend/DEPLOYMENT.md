# Tindi Tech E-commerce - Deployment Guide

## 🚀 Pre-Deployment Security Checklist

Before deploying to production, ensure you complete ALL items in this checklist:

### ✅ Environment Configuration

- [ ] **Create `.env` file on production server** based on `.env.example`
- [ ] **Set `FLASK_ENV=production`** in production `.env`
- [ ] **Generate strong `FLASK_SECRET_KEY`** (min 32 characters)
  - Run: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] **Set production MongoDB credentials** (never use dev credentials in prod)
- [ ] **Create unique admin codes** (different from development)
- [ ] **Configure CORS origins** to your actual domain only
  - Example: `CORS_ORIGINS=https://tinditech.com`

### ✅ Frontend Configuration

- [ ] **Update API URL in `site-api.js`** (line 15)
  - Change `https://api.tinditech.com` to your actual API domain
- [ ] **Test API connectivity** from frontend to backend

### ✅ Security Hardening

- [ ] **Enable HTTPS on your server** (use Let's Encrypt for free SSL)
  - Never run production without HTTPS!
  - User passwords will be transmitted in plain text without HTTPS
- [ ] **Verify debug mode is OFF** (should be automatic with `FLASK_ENV=production`)
- [ ] **Ensure `.env` file is NOT in version control**
  - Check `.gitignore` includes `.env`
- [ ] **Review CORS settings** - should ONLY include your production domain
- [ ] **Test rate limiting** is working

### ✅ Database Security

- [ ] **Enable MongoDB authentication**
- [ ] **Use IP whitelist** on MongoDB Atlas (don't allow all IPs)
- [ ] **Set up automated backups** (MongoDB Atlas has built-in backup)
- [ ] **Use read-only credentials** for any analytics/reporting tools

### ✅ Application Security

- [ ] **Change all default admin codes** from example values
- [ ] **Test token expiration** is working
- [ ] **Verify unauthorized requests are blocked**
- [ ] **Test role-based access control** (customer vs admin vs super_admin)

### ✅ Payment Integration (If Applicable)

- [ ] **Implement real M-Pesa STK Push** (currently mocked)
- [ ] **Use production API keys** (not sandbox)
- [ ] **Test payment flow end-to-end**
- [ ] **Set up payment webhooks/callbacks**

### ✅ Monitoring & Logging

- [ ] **Set up error logging** (consider Sentry or similar)
- [ ] **Monitor rate limit violations**
- [ ] **Set up uptime monitoring**
- [ ] **Configure log rotation** to prevent disk space issues

---

## 📋 Deployment Steps

### 1. Install Dependencies

On your production server:

```bash
# Navigate to backend directory
cd /path/to/PythonProject1

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your production values
nano .env  # or use your preferred editor
```

**Critical variables to set:**
- `FLASK_ENV=production`
- `FLASK_SECRET_KEY=<generate-a-strong-key>`
- `MONGODB_USERNAME=<your-production-db-user>`
- `MONGODB_PASSWORD=<your-production-db-password>`
- `SUPER_ADMIN_CODE=<unique-secure-code>`
- `ADMIN_CODE=<unique-secure-code>`
- `CORS_ORIGINS=https://yourdomain.com`

### 3. Test Configuration

```bash
# Test that configuration loads correctly
python config.py
```

You should see:
```
✓ Configuration is valid!

Environment: production
Debug Mode: False
Database Cluster: your-cluster.mongodb.net
CORS Origins: ['https://yourdomain.com']
Token Expiration: 24 hours
Rate Limiting: Enabled
```

### 4. Run Application

**For testing (not recommended for production):**
```bash
python main.py
```

**For production, use a production WSGI server (recommended):**

Install Gunicorn:
```bash
pip install gunicorn
```

Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

**Better: Use a process manager like systemd or supervisor**

Example systemd service file (`/etc/systemd/system/tinditech.service`):
```ini
[Unit]
Description=Tindi Tech E-commerce API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/PythonProject1
Environment="PATH=/path/to/PythonProject1/venv/bin"
ExecStart=/path/to/PythonProject1/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 main:app

[Install]
WantedBy=multi-user.target
```

### 5. Set Up Reverse Proxy (Nginx)

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name api.tinditech.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.tinditech.com;

    ssl_certificate /etc/letsencrypt/live/api.tinditech.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tinditech.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Deploy Frontend

1. Update `site-api.js` with production API URL
2. Upload all HTML/CSS/JS files to your web hosting
3. Test all functionality from production frontend

---

## 🔒 SSL/HTTPS Setup (Essential!)

### Using Let's Encrypt (Free)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Auto-renewal is set up automatically by certbot
```

---

## 🧪 Post-Deployment Testing

After deployment, test the following:

### Authentication
- [ ] Register a new user
- [ ] Login with correct credentials
- [ ] Login with wrong credentials (should fail)
- [ ] Test auto-login (refresh page, should stay logged in)
- [ ] Wait 24 hours and verify token expires

### Authorization
- [ ] Access admin panel as customer (should be denied)
- [ ] Access admin panel as admin (should work)
- [ ] Test super admin functions (delete user, etc.)

### Rate Limiting
- [ ] Make 6+ login attempts rapidly (should get rate limited)
- [ ] Wait 1 minute and try again (should work)

### CORS
- [ ] Make API request from your domain (should work)
- [ ] Make API request from unauthorized domain (should fail)

### Products & Orders
- [ ] View products on shop page
- [ ] Add product to cart
- [ ] Complete checkout flow
- [ ] View order in admin panel
- [ ] Update order status

---

## 🆘 Troubleshooting

### "Configuration Error: MONGODB_USERNAME is not set"
- You forgot to create `.env` file
- Solution: Copy `.env.example` to `.env` and fill in values

### "CORS error" when accessing from frontend
- Check that `CORS_ORIGINS` in `.env` includes your frontend domain
- Verify you're using HTTPS (not HTTP) in production

### Rate limit errors during testing
- Temporarily disable in `.env`: `RATE_LIMIT_ENABLED=false`
- Remember to re-enable before going live!

### Token expired immediately
- Check server time is correct
- Verify `TOKEN_EXPIRATION_HOURS` is set appropriately

---

## 📞 Support

For issues or questions:
- Review this deployment guide
- Check backend logs for error messages
- Verify all environment variables are set correctly
- Ensure database is accessible from your server
