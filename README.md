# Price Monitoring

Automated grocery price collection for major Russian retail chains. The project runs two complementary pipelines: a **fixed basket tracker** for longitudinal price analysis (CSV → Power BI), and **category catalog scrapers** that ingest full store assortments into PostgreSQL.

Built with Selenium and real browser sessions — not because it's trendy, but because these sites are SPAs with bot protection, dynamic pagination, and markup that breaks naive HTTP clients.

---

## Overview

| Pipeline | Entry point | Output | Use case |
|----------|-------------|--------|----------|
| **Basket tracker** | `main.py` | `all_products.csv` (wide format, one column per date) | Track ~400 curated SKUs daily; feed Power BI reports |
| **Category scrapers** | `cat_parse_*.py`, `category_parse_sql.py` | PostgreSQL `products` + `prices` | Broad assortment snapshots by food category |

Both pipelines share retailer-specific URL lists (`product_list.py`, `categories.py`) and the same scraping stack, but differ in scope and storage shape.

---

## Basket pipeline (`main.py`)

1. Read `all_products.csv` — columns: `Product Name`, `Product URL`, plus one date column per run.
2. Iterate retailer dicts in `product_list.py` (name → URL).
3. Fetch price via retailer-specific parser (CSS/XPath + regex).
4. Write price into the row matching **`Product URL`** (not name — URL is the join key).
5. Append today's column and save.

Helper scripts:
- `create_initial_csv.py` — bootstrap CSV from all product dicts
- `update_products_csv.py` — append new URLs from dicts without touching existing rows

## Category pipeline (`cat_parse_*.py`)

Per-retailer scripts follow the same pattern:

1. **Navigate** category URL with paginated `driver.get()`.
2. **Wait** for catalog DOM (product cards, pagination).
3. **Parse** HTML with BeautifulSoup — name, price, discount, article/SKU, canonical URL.
4. **Upsert** into PostgreSQL:
   - `products` — identity by `(shop, article)` with URL fallback; UUID primary key
   - `prices` — daily snapshot; `ON CONFLICT (product_id, date) DO UPDATE`

`category_parse_sql.py` is a multi-retailer runner (Auchan, Lenta, VkusVill, Chizhik) in one session.

---

## Tech stack

- **Python 3.13**
- **[undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)** — Chrome automation with reduced bot fingerprint
- **Selenium** — waits, element location, challenge handling
- **BeautifulSoup 4** — HTML parsing after page load
- **pandas** — CSV read/write for basket tracker
- **psycopg2** — PostgreSQL upserts
- **python-dotenv** — secrets and config
- **[Tailscale](https://tailscale.com/)** — private network to a residential proxy host; geo-restricted retailers see a normal in-country connection

---

Each retailer scraper uses a **dedicated Chrome user profile** (`chrome_profile_x` ) to preserve cookies, store selection, and session state between runs.

---

## Implementation notes

The unglamorous parts of production scraping:

**Anti-bot & session handling**
- **Geo-blocking bypass** — scrapers route Chrome through a residential proxy reachable over [Tailscale](https://tailscale.com/); local `PROXY_HOST` / `PROXY_PORT` point at the tailnet exit, so traffic exits from a home IP in-region instead of a blocked datacenter/VPN range
- Proxy enabled per retailer where needed (Dixy, Pyaterochka, etc.)
- Captcha/challenge detection for Perekrestok, Pyaterochka, etc. (`xpvnsulc` URL pattern)
- Persistent browser profiles instead of cold sessions every run

**Resilience (Magnit as the hard case)**
- Crash UI detection (`Aw, Snap!`, `chrome-error://`)
- Driver restart with URL reload; session passed back to caller
- 404 / empty catalog detection (`app-empty-404`)

**Data integrity**
- Product identity: prefer `(shop, article)`; fall back to URL for legacy rows
- Prices stored as numeric; discount kept as scraped text
- CSV basket uses stable **Product Name** for Power BI time series; URL updates in-place preserve history

**Rate limiting**
- Per-page sleeps, periodic long pauses on heavy retailers (e.g. Dixy every 5 categories)
- Randomized category order (Magnit) to reduce predictable crawl patterns

---

### Prerequisites

- Google Chrome (version must match `CHROMIUM_VERSION` in `.env`)
- PostgreSQL database `price_monitoring` (for category scrapers)
- Tailscale peer running a residential HTTP proxy (for geo-blocked retailers); scrapers use `--proxy-server` via `PROXY_HOST` / `PROXY_PORT` in `.env`
---

## Disclaimer

This project is for personal/educational use. Respect retailer terms of service, rate limits, and applicable law. Site markup and anti-bot measures change frequently — selectors and wait strategies require ongoing maintenance.
