import os
import demjson3
import undetected_chromedriver as uc
import time
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import psycopg2
from categories import *
from dotenv import load_dotenv
import csv
import uuid
from random import randint
import random

load_dotenv()

DATE_FMT = "%Y-%m-%d"
DATABASE_URL = f"postgresql://postgres:{os.environ.get('SQL_PASSWORD')}@localhost:5432/price_monitoring"
CHROMIUM_VERSION = int(os.getenv('CHROMIUM_VERSION'))

OKEY_DOSTAVKA_URL = "https://www.okeydostavka.ru"

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')

proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"

def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_2"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Mike")
    # options.add_argument(f"--proxy-server={proxy_url}")
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

loader_sel = (By.ID, "progress_bar_dialog")
def get_opacity(d):
    el = d.find_element(*loader_sel)
    # Берем computed style, а не только inline style
    return float(d.execute_script("return parseFloat(getComputedStyle(arguments[0]).opacity) || 0;", el))

def safe_click(driver, locator, timeout=20):
    # 1) Wait until element is clickable
    elem = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    # 2) Bring into view (helps with sticky headers/overlays)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
    # 3) Try native click, fallback to JS click
    try:
        elem.click()
    except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException):
        # refetch in case it became stale
        elem = driver.find_element(*locator)
        driver.execute_script("arguments[0].click();", elem)

def okey_parse_category(url: str) -> str:
    blocks = {}
    driver.get(url)
    print(url)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-price__container")))
    except Exception as e:
        print(f"Ошибка при обработке {url}: {type(e).__name__}: {repr(e)}")
        if "xpvnsulc" in driver.current_url:
            print("Captcha/challenge detected. Solve it in browser; script will auto-continue.")
            input("Press Enter to continue...")
        driver.get(url)
        time.sleep(1)
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-price__container")))
        except Exception as e:
            print(f"Ошибка при обработке {url}: {type(e).__name__}: {repr(e)}")
            if "xpvnsulc" in driver.current_url:
                print("Captcha/challenge detected. Solve it in browser; script will auto-continue.")
                input("Press Enter to continue...")
            return blocks
    time.sleep(2)
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.1) 
    driver.execute_script("window.scrollTo(0, 0);")
    html = driver.page_source
    page_blocks = okey_parse_category_page(html)
    print(len(page_blocks))
    if page_blocks:
        blocks.update(page_blocks)
    page_links = driver.find_elements(By.CSS_SELECTOR, ".pageControl.number a")
    if page_links:
        page_number = int(len(page_links)/2)
        page_links = page_links[0:page_number]
        page_idx = 1
        text = None
        for page_link in page_links:
            text = page_link.text.strip()
        last_page = int(text) if text else 1
        print(last_page)
        while page_idx < last_page:
            try:
                WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.right_arrow")))
                time.sleep(1)
                safe_click(driver, (By.CSS_SELECTOR, "a.right_arrow"), timeout=30)
                WebDriverWait(driver, 30).until(lambda d: get_opacity(d) <= 0.01)
                time.sleep(2)
                for i in range(5):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(0.1) 
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                html = driver.execute_script("return document.documentElement.outerHTML;")
                page_blocks = okey_parse_category_page(html)
                print(len(page_blocks))
                if page_blocks:
                    blocks.update(page_blocks)
                page_idx += 1
            except Exception as e:
                print(f"Ошибка при обработке {url}: {type(e).__name__}: {repr(e)}")
                if "xpvnsulc" in driver.current_url:
                    print("Captcha/challenge detected. Solve it in browser; script will auto-continue.")
                    input("Press Enter to continue...")
                else:
                    page_idx += 1
                continue
    return blocks

def okey_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="ok-theme")
    for card in cards:
        try:
            script_el = card.find("script")
            start = script_el.text.find('var product = {')
            end = script_el.text.find('};')
            brand_start = script_el.text.find('brand:')
            brand_end = script_el.text.find('category:')
            text_before_brand = script_el.text[start+14:brand_start]
            text_after_brand = script_el.text[brand_end:end+1]
            product_json = text_before_brand + text_after_brand
            product_dict = demjson3.decode(product_json)
            article = product_dict["skuId"]
            name_text = product_dict["name"]
            link = OKEY_DOSTAVKA_URL + "/msk/" + article
            price_text = product_dict["price"]
            discount_el = card.find("span", class_="label small crossed")
            discount_text = discount_el.get_text(strip=True).replace("\xa0", "").replace(",", ".").replace("₽", "").strip()
            if discount_text == "":
                discount_text = None
            page_blocks[link] = [name_text, price_text, discount_text, article]
        except Exception as e:
            print(e)
            if product_json:
                print(product_json)
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
        # driver.find_element("css selector", "label[for='is-robot']").click()
        time.sleep(2)

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver()
    time.sleep(1)
    driver.get("https://www.google.com")
    time.sleep(5)
    conn = psycopg2.connect(DATABASE_URL)
    for i in range(1):
        defeat_perekrestok_pyaterochka_robot_protection(driver, "https://www.okeydostavka.ru/msk")
        time.sleep(1)
    try:
        shop = "Окей"
        count = 0
        categories = list(OKEY_FOOD_CATEGORIES_DICT.keys())
        random.shuffle(categories)
        for category in categories:
            if count > 0 and count % 10 == 0:
                time.sleep(randint(300, 400)) 
            cat_label = OKEY_FOOD_CATEGORIES_DICT[category]
            blocks = okey_parse_category(category)
            count += 1
            time.sleep(randint(60, 70))
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()

