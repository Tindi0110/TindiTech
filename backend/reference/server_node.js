/**
 * Simple Node.js Server for M-Pesa Integration (Example)
 * 
 * To run this:
 * 1. Initialize project: npm init -y
 * 2. Install dependencies: npm install express cors body-parser axios
 * 3. Run server: node server.js
 */

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 4000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// In-memory database (for demo purposes)
const orders = {};

// --- MOCK M-PESA CREDENTIALS ---
// specific to your Daraja Portal app
const MPESA_CONFIG = {
    consumerKey: 'YOUR_CONSUMER_KEY',
    consumerSecret: 'YOUR_CONSUMER_SECRET',
    shortCode: '174379', // Test Paybill
    passkey: 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919',
    callbackUrl: 'https://mydomain.com/mpesa-callback' // Must be HTTPS and public
};

/**
 * Endpoint to create an order
 */
app.post('/create-order', (req, res) => {
    try {
        const { items, subtotal, tax, shipping, total, customer } = req.body;

        // Generate a unique Order ID
        const orderId = 'ORD-' + Date.now();

        // Save order to "database"
        orders[orderId] = {
            id: orderId,
            items,
            amount: total,
            customer,
            status: 'pending',
            payment: { status: 'unpaid' },
            createdAt: new Date()
        };

        console.log(`[ORDER CREATED] ${orderId} for KES ${total}`);

        res.json({ success: true, orderId, message: 'Order created successfully' });
    } catch (error) {
        console.error("Create Order Error:", error);
        res.status(500).json({ success: false, message: 'Internal Server Error' });
    }
});

/**
 * Endpoint to initiate STK Push
 */
app.post('/stk-push', async (req, res) => {
    const { orderId, phone } = req.body;
    const order = orders[orderId];

    if (!order) {
        return res.status(404).json({ success: false, message: 'Order not found' });
    }

    console.log(`[STK PUSH] Initiating for ${phone} Amount: ${order.amount}`);

    // --- REAL INTEGRATION WOULD GO HERE ---
    // 1. Get OAuth Token from Safaricom
    // 2. Make STK Push Request to https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest

    // For this example, we will SIMULATE a success reaction after 5 seconds
    setTimeout(() => {
        if (orders[orderId]) {
            orders[orderId].payment.status = 'paid';
            console.log(`[PAYMENT SIMULATION] Order ${orderId} marked as PAID`);
        }
    }, 10000); // 10 seconds delay to simulate user entering PIN

    res.json({ success: true, message: 'STK Push initiated successfully' });
});

/**
 * Endpoint to check order status
 */
app.get('/order/:orderId', (req, res) => {
    const { orderId } = req.params;
    const order = orders[orderId];

    if (order) {
        res.json({ success: true, order });
    } else {
        res.status(404).json({ success: false, message: 'Order not found' });
    }
});

/**
 * Endpoint to get user orders
 * Expects 'Authorization' header with user's email (for demo simplicity)
 */
app.get('/my-orders', (req, res) => {
    const userEmail = req.headers.authorization;
    if (!userEmail) {
        return res.status(401).json({ success: false, error: 'Unauthorized. Please log in.' });
    }

    // Filter orders by customer email
    const userOrders = Object.values(orders).filter(order =>
        order.customer && order.customer.email === userEmail
    );

    // Sort by newest first
    userOrders.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    res.json({ success: true, data: userOrders });
});

/**
 * Endpoint to cancel an order
 */
app.patch('/my-orders/:id/cancel', (req, res) => {
    const { id } = req.params;
    const userEmail = req.headers.authorization;

    const order = orders[id];

    if (!order) {
        return res.status(404).json({ success: false, error: 'Order not found' });
    }

    // Security check: ensure order belongs to user
    if (order.customer.email !== userEmail) {
        return res.status(403).json({ success: false, error: 'Forbidden' });
    }

    if (['pending', 'processing'].includes(order.status)) {
        order.status = 'canceled';
        console.log(`[ORDER CANCELED] ${id}`);
        res.json({ success: true, message: 'Order canceled successfully' });
    } else {
        res.status(400).json({ success: false, error: 'Order cannot be canceled' });
    }
});

/**
 * Endpoint for M-Pesa Callback (Webhook)
 */
app.post('/mpesa-callback', (req, res) => {
    // Safaricom sends payment results here
    console.log("[CALLBACK RECEIVED]", JSON.stringify(req.body, null, 2));
    // Process the result and update order status in real DB
    res.json({ result: 'ok' });
});


// Start Server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
