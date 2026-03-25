-- Products: one row per product (url is the unique identifier)
CREATE TABLE IF NOT EXISTS products (
    product_id UUID PRIMARY KEY,
    url TEXT NOT NULL,
    product_name TEXT,
    shop TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    article TEXT
);

-- If article is present, treat (shop, article) as the canonical identity.
-- This prevents duplicates even if `url` changes.
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_shop_article
    ON products(shop, article)
    WHERE article IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_url ON products(url);

-- Prices: one row per product per day (no row = product not seen that day)
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    price NUMERIC(12, 2),
    discount TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, date)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
CREATE INDEX IF NOT EXISTS idx_products_shop ON products(shop);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);