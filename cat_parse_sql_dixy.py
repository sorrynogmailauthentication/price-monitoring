import os
import chompjs
import undetected_chromedriver as uc
import time
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
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
CHROMIUM_VERSION = 147

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')
PROXY_USER = os.getenv('PROXY_USER')
PROXY_PASS = os.getenv('PROXY_PASS')

DIXY_KEY_ELEMENT = "listing__wrapper"
DIXY_PAGINATION_ELEMENT = "listing-pagination"
DIXY_ITEM_CARD_CONTAINER = "card"
DIXY_ITEM_CARD_NAME_CLASS = "card__title"
DIXY_ITEM_CARD_PRICE_CLASS = "card__price-num"
DIXY_ITEM_CARD_BEFORE_DISCOUNT_CLASS = "card__price-crossed"
DIXY_ITEM_CARD_LINK_CLASS = "card__link"
DIXY_URL = "dixy.ru"

proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"

def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_3"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument(f"--proxy-server={proxy_url}")
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

def wait_for_element(driver, class_name: str):
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
        return True
    except TimeoutException:
        return False

loader_sel = (By.ID, "progress_bar_dialog")
def get_opacity(d):
    el = d.find_element(*loader_sel)
    # Берем computed style, а не только inline style
    return float(d.execute_script("return parseFloat(getComputedStyle(arguments[0]).opacity) || 0;", el))

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

def dixy_parse_category(url: str) -> str:
    driver.get(url)
    page_links = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-pagination a")))
    html = driver.page_source
    pages_list = [el.text for el in page_links]
    last_page = int(pages_list[-1]) if pages_list else 1
    blocks = {}
    page_blocks = dixy_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    for page in range(2, last_page + 1):
        url = f"{url}?page={page}"
        print(url)
        time.sleep(20)
        driver.get(url)
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-pagination a")))
        except TimeoutException:
            input("TimeoutException")
            pass
        html = driver.page_source
        page_blocks = dixy_parse_category_page(html)
        url = url.split("?")[0]
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def dixy_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("article", class_=DIXY_ITEM_CARD_CONTAINER)
    for card in cards:
        article = card.get("product-id", "") if card else None
        name_el = card.find(class_=DIXY_ITEM_CARD_NAME_CLASS)
        name_text = name_el.get_text(strip=True) if name_el else ""
        link_el = card.find("a", class_=DIXY_ITEM_CARD_LINK_CLASS)
        link = link_el.get("href", "") if link_el else ""
        if not link:
            continue
        if link and not link.startswith("http"):
            link = DIXY_URL + link.split("?")[0]
        price_el = card.find(class_=DIXY_ITEM_CARD_PRICE_CLASS)
        price_text = price_el.get_text(strip=True).replace("руб.", "").replace(",", ".") if price_el else None
        discount_el = card.find(class_=DIXY_ITEM_CARD_BEFORE_DISCOUNT_CLASS)
        discount_text = discount_el.get_text(strip=True).replace("руб.", "").replace(",", ".") if discount_el else None
        page_blocks[link] = [name_text, price_text, discount_text, article]
    return page_blocks

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver()
    time.sleep(1)
    driver.get("https://www.google.com/search?q=dixy+dostavka")
    time.sleep(3)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        count = 0
        shop = "Дикси"
        for category in DIXY_FOOD_CATEGORIES_DICT.keys():
            if count > 0 and count % 5 == 0:
                time.sleep(100)
            count += 1
            cat_label = DIXY_FOOD_CATEGORIES_DICT[category]
            blocks = dixy_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()

