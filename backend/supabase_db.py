import requests
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_headers(token=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {token or SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    return headers

def supabase_query(table, method="GET", data=None, params=None, token=None):
    """Generic Supabase REST API caller"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"success": False, "error": "Supabase credentials missing"}
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = get_headers(token)
    
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            res = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            res = requests.patch(url, headers=headers, json=data, params=params)
        elif method == "DELETE":
            res = requests.delete(url, headers=headers, params=params)
        else:
            return {"success": False, "error": "Unsupported method"}

        res.raise_for_status()
        return {"success": True, "data": res.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- TABLE SPECIFIC WRAPPERS ---

def get_products(search=None):
    params = {"select": "*"}
    if search:
        params["name"] = f"ilike.*{search}*"
    return supabase_query("products", "GET", params=params)

def create_order(order_data):
    return supabase_query("orders", "POST", data=order_data)

def create_quote(quote_data):
    return supabase_query("quotes", "POST", data=quote_data)

def create_message(message_data):
    return supabase_query("messages", "POST", data=message_data)
