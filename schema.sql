-- Products: one row per product (url is the unique identifier)
CREATE TABLE IF NOT EXISTS products (
    url TEXT PRIMARY KEY,
    product_name TEXT,
    shop TEXT,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prices: one row per product per day (no row = product not seen that day)
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    product_url TEXT NOT NULL REFERENCES products(url) ON DELETE CASCADE,
    date DATE NOT NULL,
    price NUMERIC(12, 2),
    discount TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_url, date)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_prices_product_url ON prices(product_url);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
CREATE INDEX IF NOT EXISTS idx_products_shop ON products(shop);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);