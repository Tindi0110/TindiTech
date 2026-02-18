/**
 * site-api.js
 * Universal logic to connect Tindi Tech frontend pages to the Python Backend
 */

// ============== API CONFIGURATION ==============
function getApiUrl() {
  const hostname = window.location.hostname;
  if (hostname !== 'localhost' && hostname !== '127.0.0.1' && hostname !== '') {
    return 'https://api.tinditech.com'; // Production URL
  }
  return 'http://127.0.0.1:5000'; // Development URL
}
const API_URL = getApiUrl();
window.API_URL = API_URL; // EXPORT GLOBAL

// ============== SUPABASE CONFIGURATION ==============
// WARNING: In production, these should be environment variables or injected.
window.SUPABASE_URL = ""; // SET BY USER
window.SUPABASE_KEY = ""; // SET BY USER (Anon Key)

function initSupabase() {
  if (typeof supabase === 'undefined') {
    console.warn("Supabase library not loaded. Scripts using Supabase will fail.");
    return null;
  }
  if (!window.SUPABASE_URL || !window.SUPABASE_KEY) {
    console.warn("Supabase credentials missing. Run setup or provide them.");
    return null;
  }
  return supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);
}

// Lazy init
let supabaseClient = null;
window.getSupabase = function() {
  if (!supabaseClient) supabaseClient = initSupabase();
  return supabaseClient;
};

// ============== GLOBAL AUTH UTILS ==============
window.saveUserSession = function(session, role = 'customer') {
  const storage = localStorage; // Default to persistent for now
  storage.setItem("sb-token", session.access_token);
  storage.setItem("user_role", role);
  storage.setItem("user_name", session.user.email);
};

window.clearUserSession = function() {
  localStorage.removeItem("sb-token");
  localStorage.removeItem("user_role");
  localStorage.removeItem("user_name");
};

// ============== GLOBAL UTILS ==============
const COUNTRY_CODES = [
  { code: "+254", name: "Kenya" },
  { code: "+1", name: "USA/Canada" },
  { code: "+44", name: "UK" },
  { code: "+256", name: "Uganda" },
  { code: "+255", name: "Tanzania" },
  { code: "+250", name: "Rwanda" },
  { code: "+251", name: "Ethiopia" },
  { code: "+252", name: "Somalia" },
  { code: "+27", name: "South Africa" },
  { code: "+234", name: "Nigeria" },
  { code: "+233", name: "Ghana" },
  { code: "+91", name: "India" },
  { code: "+86", name: "China" },
  { code: "+971", name: "UAE" },
  { code: "+49", name: "Germany" },
  { code: "+33", name: "France" },
  { code: "+81", name: "Japan" },
  { code: "+61", name: "Australia" }
  // Add more as needed or use a full library if requested, but this covers major usage
];

window.populateCountryCodes = function (selectId, defaultCode = "+254") {
  const select = document.getElementById(selectId);
  if (!select) return;
  select.innerHTML = '';
  COUNTRY_CODES.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.code;
    opt.innerText = `${c.name} (${c.code})`;
    if (c.code === defaultCode) opt.selected = true;
    select.appendChild(opt);
  });
};

/* Attempt to auto-populate common IDs on load */
document.addEventListener('DOMContentLoaded', () => {
  if (window.populateCountryCodes) {
    ['country_code', 'country-code', 'phone-code'].forEach(id => window.populateCountryCodes(id));
  }
});

// ============== NOTIFICATION SYSTEM (Toasts & Modals) ==============
function injectNotificationStyles() {
  if (document.getElementById('notify-styles')) return;
  const style = document.createElement('style');
  style.id = 'notify-styles';
  style.innerHTML = `
    /* TOASTS */
    #toast-container { position: fixed; top: 20px; right: 20px; z-index: 10000; display: flex; flex-direction: column; gap: 10px; }
    .toast { min-width: 250px; padding: 15px 20px; border-radius: 8px; color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.15); animation: slideInRight 0.3s ease-out; display: flex; align-items: center; justify-content: space-between; font-size: 14px; opacity: 0.95; }
    .toast.success { background-color: #28a745; }
    .toast.error { background-color: #dc3545; }
    .toast.info { background-color: #17a2b8; }
    .toast.warning { background-color: #ffc107; color: #333; }
    @keyframes slideInRight { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    @keyframes fadeOutRight { from { opacity: 1; } to { opacity: 0; transform: translateX(100%); } }

    /* CONFIRM MODAL */
    #globalConfirmModal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10001; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
    .confirm-content { background: white; padding: 25px; border-radius: 12px; width: 90%; max-width: 400px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); animation: popIn 0.2s ease-out; }
    .confirm-title { font-size: 18px; font-weight: 600; margin-bottom: 10px; color: #333; }
    .confirm-msg { font-size: 15px; color: #666; margin-bottom: 25px; line-height: 1.5; }
    .confirm-actions { display: flex; justify-content: center; gap: 15px; }
    .confirm-btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: opacity 0.2s; }
    .confirm-btn:hover { opacity: 0.9; }
    .confirm-yes { background: #dc3545; color: white; }
    .confirm-no { background: #e0e0e0; color: #333; }
    @keyframes popIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
  `;
  document.head.appendChild(style);

  // Inject Toast Container
  if (!document.getElementById('toast-container')) {
    const div = document.createElement('div');
    div.id = 'toast-container';
    document.body.appendChild(div);
  }

  // Inject Confirm Modal
  if (!document.getElementById('globalConfirmModal')) {
    const modal = document.createElement('div');
    modal.id = 'globalConfirmModal';
    modal.innerHTML = `
      <div class="confirm-content">
        <div class="confirm-title">Confirm Action</div>
        <div class="confirm-msg" id="globalConfirmMsg">Are you sure?</div>
        <div class="confirm-actions">
           <button class="confirm-btn confirm-no" id="globalConfirmNo">Cancel</button>
           <button class="confirm-btn confirm-yes" id="globalConfirmYes">Confirm</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
}

window.showToast = function (message, type = 'info') {
  injectNotificationStyles();
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  // Icons based on type
  let icon = '';
  if (type === 'success') icon = '✓';
  else if (type === 'error') icon = '✕';
  else if (type === 'warning') icon = '⚠';
  else icon = 'ℹ';

  toast.innerHTML = `
    <div style="display:flex; align-items:center; gap:10px;">
      <span style="font-weight:bold; font-size:18px;">${icon}</span>
      <span>${message}</span>
    </div>
  `;

  container.appendChild(toast);

  // Auto remove
  setTimeout(() => {
    toast.style.animation = 'fadeOutRight 0.5s forwards';
    setTimeout(() => toast.remove(), 500);
  }, 3500);
};

window.secureConfirm = function (message, confirmText = "Confirm", isDangerous = false) {
  injectNotificationStyles();
  return new Promise((resolve) => {
    const modal = document.getElementById('globalConfirmModal');
    const msgEl = document.getElementById('globalConfirmMsg');
    const yesBtn = document.getElementById('globalConfirmYes');
    const noBtn = document.getElementById('globalConfirmNo');

    msgEl.innerText = message;
    yesBtn.innerText = confirmText;

    // Style adjustments for dangerous actions
    if (isDangerous) {
      yesBtn.style.backgroundColor = "#dc3545"; // Red
    } else {
      yesBtn.style.backgroundColor = "#007bff"; // Blue
    }

    modal.style.display = 'flex';

    const cleanUp = () => {
      modal.style.display = 'none';
      yesBtn.onclick = null;
      noBtn.onclick = null;
    };

    yesBtn.onclick = () => { cleanUp(); resolve(true); };
    noBtn.onclick = () => { cleanUp(); resolve(false); };

    // Click outside to close (Cancel)
    modal.onclick = (e) => {
      if (e.target === modal) { cleanUp(); resolve(false); }
    }
  });
};


// ============== 1. GLOBAL QUOTE MODAL SYSTEM ==============
// Injects the modal HTML into the page automatically
function injectQuoteModal() {
  if (document.getElementById('globalQuoteModal')) return;

  const modalHTML = `
  <div id="globalQuoteModal" class="modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:9999; backdrop-filter:blur(5px); align-items:center; justify-content:center;">
    <div class="modal-content" style="background:white; padding:30px; border-radius:15px; width:90%; max-width:500px; position:relative; box-shadow: 0 10px 30px rgba(0,0,0,0.2); animation: slideUp 0.3s ease-out;">
      <span class="close-modal" onclick="closeQuoteModal()" style="position:absolute; top:15px; right:20px; font-size:24px; cursor:pointer; color:#777;">&times;</span>
      
      <h2 style="color:var(--primary-color, #007bff); text-align:center; margin-bottom:10px;">Get a Free Quote</h2>
      <p style="text-align:center; color:#666; margin-bottom:20px;">Tell us about your project needs.</p>
      
      <form id="globalQuoteForm">
        <div style="margin-bottom:15px;">
          <input type="text" name="name" placeholder="Your Name" required style="width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px;">
        </div>
        <div style="margin-bottom:15px;">
          <input type="email" name="email" placeholder="Email Address" required style="width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px;">
        </div>
        <div style="margin-bottom:15px; display:flex; gap:10px; align-items:center;">
          <select id="country_code_modal" name="country_code" style="width:120px; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px; background:white; cursor:pointer;"></select>
          <input type="tel" name="phone" placeholder="Phone Number" required style="flex:1; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px;">
        </div>
        <div style="margin-bottom:15px;">
           <select name="service" style="width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px; background:white;">
              <option value="General">General Inquiry</option>
              <option value="Networking">Networking & Cabling</option>
              <option value="CCTV">CCTV & Security</option>
              <option value="Web Design">Web Design / Development</option>
              <option value="Starlink">Starlink Installation</option>
           </select>
        </div>
        <div style="margin-bottom:20px;">
          <textarea name="message" rows="4" placeholder="Describe your requirements..." required style="width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:16px; font-family:inherit;"></textarea>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%; padding:12px; font-size:18px; border:none; border-radius:8px; background:var(--primary-color, #007bff); color:white; cursor:pointer; font-weight:bold; transition: opacity 0.3s;">
          Request Quote
        </button>
      </form>
    </div>
  </div>
  <style>
    @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  </style>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHTML);

  // Setup Form Listener
  document.getElementById('globalQuoteForm').addEventListener('submit', handleQuoteSubmit);

  // Populate Country Codes for Modal
  if (window.populateCountryCodes) {
    window.populateCountryCodes('country_code_modal', '+254');
  }
}

window.openQuoteModal = function () {
  const modal = document.getElementById('globalQuoteModal');
  if (modal) modal.style.display = 'flex';
}

window.closeQuoteModal = function () {
  const modal = document.getElementById('globalQuoteModal');
  if (modal) modal.style.display = 'none';
}

// Hijack all links to quote.html
function initGlobalQuoteLinks() {
  document.querySelectorAll('a[href="quote.html"], a[href="quote.html#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      openQuoteModal();
    });
  });
}

// Global Form Handler
async function handleQuoteSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const originalText = btn.innerText;

  btn.innerText = 'Sending...';
  btn.style.opacity = '0.7';
  btn.disabled = true;

  const formData = new FormData(form);
  const rawData = Object.fromEntries(formData.entries());

  // Merge phone with country code
  const data = {
    ...rawData,
    phone: ((rawData.country_code || "") + (rawData.phone || "")).replace(/\s+/g, '')
  };

  try {
    const res = await fetch(`${API_URL}/quote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();

    if (json.success) {
      showToast('Request Received! We will contact you shortly.', 'success');
      form.reset();
      closeQuoteModal();
    } else {
      showToast('Error: ' + (json.error || 'Unknown error occurred'), 'error');
    }
  } catch (err) {
    showToast('Connection Failed. Ensure backend is running.', 'error');
  } finally {
    btn.innerText = originalText;
    btn.style.opacity = '1';
    btn.disabled = false;
  }
}

// ============== 2. PRODUCT FETCHING ==============
async function fetchProducts(query = '') {
  const container = document.querySelector('.products-grid');
  if (!container) return;

  container.innerHTML = '<p class="text-center" style="width: 100%; padding: 40px; color:#666;">Loading premium products...</p>';
  try {
    const url = query ? `${API_URL}/products?search=${encodeURIComponent(query)}` : `${API_URL}/products`;
    const response = await fetch(url);
    const json = await response.json();

    if (json.success && json.data.length > 0) {
      container.innerHTML = '';
      window.allProducts = json.data;

      function escapeHtml(text) {
        if (!text) return text;
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      }

      json.data.forEach(product => {
        const card = document.createElement('div');
        card.className = 'product-card';

        // Stock Logic
        const stock = (product.stock !== undefined && product.stock !== null) ? parseInt(product.stock) : 0;
        const isOutOfStock = stock <= 0;

        // Indirect Stock Display
        let stockDisplay = '';
        if (isOutOfStock) {
          stockDisplay = `<div style="color:#dc3545; font-weight:bold; font-size:0.9em; margin-bottom:5px;">Out of Stock</div>`;
        } else if (stock > 10) {
          stockDisplay = `<div style="color:#28a745; font-weight:bold; font-size:0.9em; margin-bottom:5px;">In Stock (10+ available)</div>`;
        } else {
          stockDisplay = `<div style="color:#d39e00; font-weight:bold; font-size:0.9em; margin-bottom:5px;">Low Stock (Only ${stock} left!)</div>`;
        }

        // Quantity Input & Button
        let actionHtml = '';
        if (isOutOfStock) {
          actionHtml = `<button class="btn btn-primary" style="padding: 5px 12px; opacity:0.6; cursor:not-allowed;" disabled>Out of Stock</button>`;
        } else {
          actionHtml = `
            <div style="display:flex; align-items:center; gap:5px; justify-content:center;">
                <input type="number" id="qty-${product._id || product.id}" value="1" min="1" max="${stock}" style="width:50px; padding:5px; border:1px solid #ddd; border-radius:4px;">
                <button class="btn btn-primary" style="padding: 5px 12px;" 
                    onclick="addToCart('${escapeHtml(product.name)}', ${product.price}, '${escapeHtml(product.image)}', ${stock}, document.getElementById('qty-${product._id || product.id}').value)">
                  Add to Cart
                </button>
            </div>
            `;
        }

        card.innerHTML = `
          <div class="product-img-wrapper">
            <img src="${product.image || 'img/pics/default-product.png'}" class="product-img" alt="${escapeHtml(product.name)}">
          </div>
          <div class="product-info">
            <h3>${escapeHtml(product.name)}</h3>
            <div class="product-price">${parseFloat(product.price).toLocaleString()} KES</div>
            <div class="product-category">${escapeHtml(product.category || 'Product')}</div>
            ${stockDisplay}
            
            <div style="margin-top: 10px;">
                ${actionHtml}
                <button class="btn btn-outline" style="padding: 5px 12px; margin-top:5px; width:100%;" onclick="openDetailModal('${product._id || product.id}')">
                   View More
                </button>
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    } else {
      container.innerHTML = '<p class="text-center" style="width: 100%;">No products found.</p>';
    }
  } catch (error) {
    container.innerHTML = `<div style="text-align:center; color:#721c24; background-color:#f8d7da; border-color:#f5c6cb; padding:20px; border-radius:5px; margin:20px;">
        <h3>⚠️ Connection Failed</h3>
        <p>Could not load products. Please ensure the backend server is running.</p>
        <code style="display:block; margin-top:10px; font-size:0.8em;">Target: ${API_URL}</code>
    </div>`;
  }
}

// ============== 3. CONTACT FORM ==============
function setupContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;
  form.addEventListener('submit', handleQuoteSubmit); // Reuse logic if fields match, or simple fetch
}

// ============== 4. PROFESSIONAL CART MANAGER ==============
class CartManager {
  constructor() {
    this.storageKey = 'cart';
    this.cart = this.load();
  }

  load() {
    try {
      const data = localStorage.getItem(this.storageKey);
      if (!data) return [];
      const parsed = JSON.parse(data);
      if (!Array.isArray(parsed)) return [];
      return this.validate(parsed);
    } catch (e) {
      return [];
    }
  }

  validate(cart) {
    // Ensure each item has required fields and proper types
    return cart.filter(item =>
      item &&
      typeof item.name === 'string' &&
      typeof item.price === 'number' &&
      typeof item.quantity === 'number' &&
      item.quantity > 0
    );
  }

  save() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.cart));
    updateCartCount();
  }

  addItem(name, price, image, maxStock, qtyToAdd) {
    const qty = parseInt(qtyToAdd, 10);
    const limit = parseInt(maxStock, 10) || 999;

    if (isNaN(qty) || qty < 1) {
      if (window.showToast) window.showToast("Please enter a valid quantity.", "warning");
      return false;
    }

    if (qty > limit) {
      if (window.showToast) window.showToast(`Sorry, only ${limit} units available.`, "warning");
      return false;
    }

    const existing = this.cart.find(i => i.name === name);
    if (existing) {
      const currentQty = parseInt(existing.quantity, 10) || 0;
      const newTotal = currentQty + qty;

      if (newTotal > limit) {
        if (window.showToast) window.showToast(`Stock limit reached! You have ${currentQty} in cart.`, "warning");
        return false;
      }
      existing.quantity = newTotal;
      existing.maxStock = limit;
    } else {
      this.cart.push({ name, price, image, quantity: qty, maxStock: limit });
    }

    this.save();
    if (window.showToast) window.showToast(`${qty} x ${name} added to cart!`, 'success');
    return true;
  }

  updateQuantity(index, newQty) {
    if (this.cart[index]) {
      const qty = parseInt(newQty, 10);
      const limit = parseInt(this.cart[index].maxStock, 10) || 999;

      if (qty > limit) {
        if (window.showToast) window.showToast(`Sorry, only ${limit} units available in stock.`, 'warning');
        return false;
      }

      this.cart[index].quantity = qty;
      if (this.cart[index].quantity <= 0) {
        this.cart.splice(index, 1);
      }
      this.save();
      return true;
    }
    return false;
  }

  removeItem(index) {
    if (this.cart[index]) {
      this.cart.splice(index, 1);
      this.save();
      return true;
    }
    return false;
  }

  getTotal() {
    return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }

  getCount() {
    return this.cart.reduce((acc, item) => acc + (item.quantity || 1), 0);
  }

  clear() {
    this.cart = [];
    this.save();
  }
}

// Global instance
window.cartManager = new CartManager();

// Legacy wrapper for compatibility with existing onclick attributes
window.addToCart = function (name, price, image, maxStock, qtyToAdd) {
  return window.cartManager.addItem(name, price, image, maxStock, qtyToAdd);
};

function updateCartCount() {
  const el = document.getElementById('cart-count');
  if (el) {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem("cart")) || []; } catch (e) { }
    el.innerText = cart.reduce((acc, item) => acc + (item.quantity || 1), 0);
  }
}

// Product Detail Modal
window.openDetailModal = function (id) {
  const product = (window.allProducts || []).find(p => (p._id || p.id) === id);
  if (!product) return;
  const modal = document.getElementById('productDetailModal');
  if (!modal) return;

  document.getElementById('detailImg').src = product.image || 'img/pics/default-product.png';
  document.getElementById('detailName').innerText = product.name;
  document.getElementById('detailPrice').innerText = parseFloat(product.price).toLocaleString() + ' KES';
  document.getElementById('detailDesc').innerText = product.description || 'No description.';

  const addBtn = document.getElementById('detailAddBtn');
  const stock = (product.stock !== undefined && product.stock !== null) ? parseInt(product.stock) : 0;

  // Detail Modal Stock Display
  if (stock <= 0) {
    addBtn.innerText = "Out of Stock";
    addBtn.disabled = true;
    addBtn.style.opacity = "0.6";
    addBtn.style.cursor = "not-allowed";
    addBtn.onclick = null;
  } else {
    addBtn.innerText = "Add to Cart";
    addBtn.disabled = false;
    addBtn.style.opacity = "1";
    addBtn.style.cursor = "pointer";
    addBtn.onclick = () => {
      addToCart(product.name, product.price, product.image, stock);
      modal.style.display = 'none';
    };
  }
  modal.style.display = 'flex';
};

window.closeDetailModal = function () {
  const modal = document.getElementById('productDetailModal');
  if (modal) modal.style.display = 'none';
};

// Close modals on outside click
window.onclick = function (event) {
  const modals = ['productDetailModal', 'globalQuoteModal', 'productModal']; // List of all possible modals
  modals.forEach(id => {
    const modal = document.getElementById(id);
    if (modal && event.target == modal) {
      modal.style.display = "none";
    }
  });
};

// ============== INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', () => {
  injectQuoteModal(); // Create the modal HTML
  initGlobalQuoteLinks(); // Hijack links
  fetchProducts(); // Load shop
  updateCartCount(); // Update badge
});
