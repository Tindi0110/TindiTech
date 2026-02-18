-- Tindi Tech Supabase Schema

-- 1. PRODUCTS TABLE
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    image TEXT,
    category TEXT,
    stock INTEGER DEFAULT 0,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. ORDERS TABLE
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    items JSONB NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. QUOTES TABLE
CREATE TABLE IF NOT EXISTS public.quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    service TEXT,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. MESSAGES TABLE
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ENABLE RLS (Security)
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- PUBLIC SELECT FOR PRODUCTS
CREATE POLICY "Public read for products" ON public.products FOR SELECT USING (true);

-- PUBLIC INSERT FOR ORDERS, QUOTES, MESSAGES
CREATE POLICY "Public insert for orders" ON public.orders FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert for quotes" ON public.quotes FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert for messages" ON public.messages FOR INSERT WITH CHECK (true);
