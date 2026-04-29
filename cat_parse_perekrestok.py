import os
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

PEREKRESTOK_URL = "https://www.perekrestok.ru"

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')
PROXY_USER = os.getenv('PROXY_USER')
PROXY_PASS = os.getenv('PROXY_PASS')

proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"

def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_4"
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

def perekrestok_parse_category(url: str) -> str:
    blocks = {}
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-card__price")))
    except (Exception, TimeoutException) as e:
        print(f"TimeoutException {url}: {type(e).__name__}: {repr(e)}")
        if "xpvnsulc" in driver.current_url:
            print("Captcha/challenge detected. Solve it in browser; script will auto-continue.")
            input("Press Enter to continue...")
            time.sleep(2)
        try:
            driver.get(url)
            time.sleep(1)
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-card__price")))
        except TimeoutException:
            print(f"TimeoutException {url}: {type(e).__name__}: {repr(e)}")
            return blocks
    time.sleep(1)
    print(url)
    html = driver.page_source
    page_blocks = perekrestok_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    print(len(page_blocks))
    return blocks

def perekrestok_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="product-card-wrapper")
    for card in cards:
        try:
            link_el = card.find("a", class_="product-card__title")
            link_text = link_el.get("href", "") if link_el else ""
            link = PEREKRESTOK_URL + link_text
            article = link_text.split("-")[-1]
            name_el = card.find("a", class_="product-card__title-link")
            name_text = name_el.get_text(strip=True) if name_el else ""
            price_el = card.find("div", class_="price-new")
            texts = list(price_el.stripped_strings) 
            price = texts[1] if len(texts) > 1 else texts[0]
            price_text = price.replace('\xa0', '').replace(',', '.').replace('₽', '').strip()
            discount_el = card.find("div", class_="price-old")
            if discount_el:
                texts = list(discount_el.stripped_strings) 
                discount = texts[1] if len(texts) > 1 else texts[0]
                discount_text = discount.replace('\xa0', '').replace(',', '.').replace('₽', '').strip()
            else:
                discount_text = None
            page_blocks[link] = [name_text, price_text, discount_text, article]
        except Exception as e:
            print(e)
            continue
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

def wait_until_challenge_cleared(driver, timeout=120):
    WebDriverWait(driver, timeout).until(lambda d: "xpvnsulc" not in (d.current_url or "").lower())

def defeat_perekrestok_pyaterochka_robot_protection(driver, url):
    driver.get(url)
    time.sleep(5)
    if "xpvnsulc" in driver.current_url:
        print("Captcha/challenge detected. Solve it in browser; script will auto-continue.")
        wait_until_challenge_cleared(driver, timeout=180)
        time.sleep(2)

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver()
    time.sleep(1)
    driver.get("https://www.google.com/search?q=perekrestok+dostavka")
    time.sleep(3)
    conn = psycopg2.connect(DATABASE_URL)
    for i in range(1):
        defeat_perekrestok_pyaterochka_robot_protection(driver, PEREKRESTOK_URL)
        time.sleep(5)
    try:
        shop = "Перекресток"
        count = 0
        for category in PEREKRESTOK_FOOD_CATEGORIES_DICT.keys():
            if count > 0 and count % 20 == 0:
                time.sleep(360)
            cat_label = PEREKRESTOK_FOOD_CATEGORIES_DICT[category]
            blocks = perekrestok_parse_category(category)
            count += 1
            time.sleep(25)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()