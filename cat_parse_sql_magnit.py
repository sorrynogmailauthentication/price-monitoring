import os
import undetected_chromedriver as uc
import time
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import psycopg2
from categories import *
from dotenv import load_dotenv
import csv
import uuid

load_dotenv()

DATE_FMT = "%Y-%m-%d"
DATABASE_URL = f"postgresql://postgres:{os.environ.get('SQL_PASSWORD')}@localhost:5432/price_monitoring"
CHROMIUM_VERSION = int(os.getenv('CHROMIUM_VERSION'))

MAGNIT_URL = "https://magnit.ru"

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')

proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"

def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_5"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Mike")
    # options.add_argument(f"--proxy-server={proxy_url}")
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

def magnit_parse_category(url: str) -> str:
    blocks = {}
    driver.get(url)
    print(url)
    WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "unit-catalog__stack-item")))
    html = driver.page_source
    page_blocks = magnit_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    soup = BeautifulSoup(html, "html.parser")
    pagination_el = soup.find("nav", class_="pl-pagination__pager")
    if pagination_el:
        pagination_pages = pagination_el.find_all("li")
        last_page_span = pagination_pages[-1].find("span", class_="pl-button__icon")
        last_page = int(last_page_span.get_text(strip=True))
    else:
        last_page = 1
    for i in range(2, last_page + 1):
        page_url = f"{url}?page={i}"
        driver.get(page_url)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "unit-catalog__stack-item")))
        html = driver.page_source
        page_blocks = magnit_parse_category_page(html)
        print(len(page_blocks))
        if page_blocks:
            blocks.update(page_blocks)
        time.sleep(1)
    return blocks

def magnit_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="unit-catalog__stack-item")
    for card in cards:
        first_child = card.find("article", recursive=False)
        if not first_child:
            continue
        name_el = card.find("a")
        name = name_el.get("title").strip()
        link = MAGNIT_URL + name_el.get("href").split("?")[0]
        article = link.split("/")[-1].split("-")[0]
        price_el = card.find("span", class_="unit-catalog-product-preview-prices__regular")
        price = price_el.find("span").get_text(strip=True).split("\u200a")[0]
        discount_el = card.find("span", class_="unit-catalog-product-preview-prices__sale")
        if discount_el:
            discount = discount_el.find("span").get_text(strip=True).split("\u200a")[0]
        else:
            discount = None
        page_blocks[link] = [name, price, discount, article]
    return page_blocks

def _parse_price(price_text):
    """Convert scraped price string (e.g. '89,99') to numeric or None."""
    if not price_text:
        return None
    try:
        s = str(price_text).strip().replace(",", ".").replace(" ", "").replace("\u2009", "")
        return float(s) if s else None
    except (ValueError, TypeError):
        return None

def update_or_append_products_sql(conn, blocks: dict, today: str, shop: str, cat_label: str) -> None:
    """Upsert products and today's prices into PostgreSQL."""
    with conn.cursor() as cur:
        for url, (name, price_text, discount_text, article) in blocks.items():
            # Normalize missing identifiers to NULL (important for unique constraints).
            if article == "":
                article = None

            # Canonical identity:
            # - prefer (shop, article) when article exists
            # - otherwise fall back to `url` lookup
            product_id = None

            if article:
                cur.execute("SELECT product_id FROM products WHERE shop = %s AND article = %s LIMIT 1", (shop, article))
                row = cur.fetchone()
                if row:
                    product_id = row[0]

            if product_id is None:
                cur.execute("SELECT product_id FROM products WHERE url = %s LIMIT 1", (url,))
                row = cur.fetchone()
                if row:
                    product_id = row[0]

            if product_id is None:
                # Generate UUID in code (not in DB)
                product_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO products (product_id, url, product_name, shop, category, article) VALUES (%s, %s, %s, %s, %s, %s)",
                    (product_id, url, name or None, shop, cat_label, article),
                )
            else:
                # Update product attributes; keep canonical (shop, article) identity.
                cur.execute("""
                UPDATE products SET url = %s, product_name = %s, shop = %s, category = %s, article = COALESCE(products.article, %s) 
                WHERE product_id = %s""",
                    (url, name or None, shop, cat_label, article, product_id),
                )
            # Upsert price for today
            price_num = _parse_price(price_text)
            cur.execute(
                """
                INSERT INTO prices (product_id, date, price, discount) VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_id, date) DO UPDATE SET price = EXCLUDED.price, discount = EXCLUDED.discount
                """,
                (product_id, today, price_num, discount_text),
            )
    conn.commit()

def test_write_to_csv(blocks: dict, filename: str):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Product Name", "Price", "Discount", "Article"])
        for url, (name, price, discount, article) in blocks.items():
            writer.writerow([url, name, price, discount, article])

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver()
    time.sleep(1)
    driver.get("https://www.google.com")
    time.sleep(1)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        shop = "Магнит"
        categories = list(MAGNIT_FOOD_CATEGORIES_DICT.keys())
        for category in categories:
            cat_label = MAGNIT_FOOD_CATEGORIES_DICT[category]
            blocks = magnit_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()

