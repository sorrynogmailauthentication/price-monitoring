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
import re
import uuid

load_dotenv()

DATE_FMT = "%Y-%m-%d"
DATABASE_URL = f"postgresql://postgres:{os.environ.get('SQL_PASSWORD')}@localhost:5432/price_monitoring"
CHROMIUM_VERSION = 146

LENTA_PAGINATION_ELEMENT = "pagination-nav__list"
LENTA_PRICE_ELEMENT = "main-price"
LENTA_ARTICLE_REGEX = re.compile(r"product-(\d+)-favorite")
LENTA_CARD_CONTAINER = "div[class='lu-grid']"
LENTA_URL = "https://lenta.com/"

AUCHAN_KEY_ELEMENT = "styles_productCard__xH9l_"
AUCHAN_PAGINATION_ELEMENT = "styles_pagination__TCaLO"
AUCHAN_ITEM_CARD_CONTAINER = "div[data-testid='productCard-container']"
AUCHAN_ITEM_CARD_NAME_CLASS = "styles_productCardContentPanel_name__gtZfG"
AUCHAN_ITEM_CARD_PRICE_CLASS = "styles_price__U1y_f"
AUCHAN_ITEM_CARD_BEFORE_DISCOUNT_CLASS = "styles_price__oldPrice__VsVTT"
AUCHAN_ITEM_CARD_LINK_CLASS = "styles_productCardPicturePanel__sR0Mr"
AUCHAN_URL = "https://www.auchan.ru"
AUCHAN_ARTICLE_REGEX = re.compile(r'_(\d+?)_')

DIXY_KEY_ELEMENT = "listing__wrapper"
DIXY_PAGINATION_ELEMENT = "listing-pagination"
DIXY_ITEM_CARD_CONTAINER = "card"
DIXY_ITEM_CARD_NAME_CLASS = "card__title"
DIXY_ITEM_CARD_PRICE_CLASS = "card__price-num"
DIXY_ITEM_CARD_BEFORE_DISCOUNT_CLASS = "card__price-crossed"
DIXY_ITEM_CARD_LINK_CLASS = "card__link"
DIXY_URL = "dixy.ru"
CHIZHIK_URL = "https://chizhik.club"

def get_driver():
    options = uc.ChromeOptions()
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

def get_driver_no_images():
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_1"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

def wait_for_element(driver, class_name: str):
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
        return True
    except TimeoutException:
        return False

def get_auchan_category_list() -> list:
    driver.get(AUCHAN_URL)
    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(1)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    base = AUCHAN_URL
    links = [
        base + a["href"] if a.get("href", "").startswith("/") else a["href"]
        for a in soup.select("#gtm-youMayNeed-section a.styles_category__4nwCg[href]")
    ]
    return links

def lenta_parse_category(url: str) -> str:
    driver.get(url)
    wait_for_element(driver, LENTA_PRICE_ELEMENT)
    time.sleep(0.5)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all("ul", class_=LENTA_PAGINATION_ELEMENT)
    last_page = 1
    if pages:
        for page in pages:
            raw_value = page.get_text(strip=True, separator=",")
            last_page = int(raw_value.split(",")[-1])
    blocks = {}
    page_blocks = lenta_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    base_url = url.rstrip("/")
    for page in range(2, last_page + 1):
        url = f"{base_url}/page/{page}/" 
        driver.get(url)
        wait_for_element(driver, LENTA_PRICE_ELEMENT)
        time.sleep(0.2)
        html = driver.page_source
        page_blocks = lenta_parse_category_page(html)
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def lenta_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    card_container = soup.select(LENTA_CARD_CONTAINER)
    cards = card_container[0].find_all("div", class_="lu-grid__item")
    for card in cards:
        article = None
        name_el = card.find("span", class_="card-name_content")
        name_appendix_el = card.find("p", class_="card-name_package")
        name_text = name_el.get_text(strip=True) if name_el else ""
        name_appendix_text = name_appendix_el.get_text(strip=True) if name_appendix_el else ""
        name_text = f"{name_text} {name_appendix_text}"
        link_el = card.find("a", class_="product-card")
        link = link_el.get("href", "") if link_el else ""
        price_el = card.find("span", class_="main-price")
        price_text = price_el.get_text(strip=True).replace("₽", "").replace(",", ".").replace("\xa0", "") if price_el else None
        discount_el = card.find("span", class_="discount-badge")
        article_el = card.find("button", class_="product-card-favorite-btn")
        raw_id = article_el.get("id", "") if article_el else None
        if raw_id:
            article_match = LENTA_ARTICLE_REGEX.search(raw_id)
            article = str(article_match.group(1)).zfill(6) if article_match else None
        if discount_el:
            old_price_el = card.find("div", class_="old-price")
            old_price_text = old_price_el.get_text(strip=True).replace("₽", "").replace(",", ".").replace("\xa0", "").split("-")[0] if old_price_el else None
        else:
            old_price_text = None
        page_blocks[link] = [name_text, price_text, old_price_text, article]
    return page_blocks

def auchan_parse_category(url: str) -> str:
    driver.get(url)
    wait_for_element(driver, AUCHAN_KEY_ELEMENT)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find("ul", class_=AUCHAN_PAGINATION_ELEMENT)
    pages_text = pages.get_text(strip=True, separator=",").split(",")[-1] if pages else None
    last_page = int(pages_text) if pages_text else 1
    blocks = {}
    page_blocks = auchan_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    for page in range(2, last_page + 1):
        url = f"{url}?page={page}"
        driver.get(url)
        wait_for_element(driver, AUCHAN_KEY_ELEMENT)
        url = url.split("?")[0]
        html = driver.page_source
        page_blocks = auchan_parse_category_page(html)
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def auchan_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(AUCHAN_ITEM_CARD_CONTAINER)
    for card in cards:
        article_el = card.find("img")
        article_html = article_el.get("src", "") if article_el else None
        article_match = AUCHAN_ARTICLE_REGEX.search(article_html)
        article = str(article_match.group(1)).zfill(6) if article_match else None
        name_el = card.find(class_=AUCHAN_ITEM_CARD_NAME_CLASS)
        name_text = name_el.get_text(strip=True) if name_el else ""
        link_el = card.find("a", class_=AUCHAN_ITEM_CARD_LINK_CLASS)
        link = link_el.get("href", "") if link_el else ""
        if not link:
            continue
        if link and not link.startswith("http"):
            link = AUCHAN_URL + link.split("?")[0]
        price_el = card.find(class_=AUCHAN_ITEM_CARD_PRICE_CLASS)
        price_text = price_el.get_text(strip=True).replace("₽", "").replace(",", ".") if price_el else None
        discount_el = card.find(class_=AUCHAN_ITEM_CARD_BEFORE_DISCOUNT_CLASS)
        discount_text = discount_el.get_text(strip=True).replace("₽", "").replace(",", ".") if discount_el else None
        page_blocks[link] = [name_text, price_text, discount_text, article]
    return page_blocks

def dixy_parse_category(url: str) -> str:
    driver.get(url)
    page_links = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-pagination a")))
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
        time.sleep(12)
        driver.get(url)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-pagination a")))
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

def chizhik_parse_category(url: str) -> str:
    driver.get(url)
    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(3)
    for i in range(30):
        driver.execute_script("document.body.scrollTop += 2000;")
        time.sleep(0.1) 
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    page_blocks = {}
    cards = soup.find_all("div", class_="css-6n4fw9")
    for card in cards:
        not_in_stock = card.find(class_="css-3hcm5q")
        if not_in_stock:
            continue
        article_el = card.find(class_="css-1ovawgy")
        article = article_el.get("data-qa", "").split("-")[-1] if article_el else None
        name_el = card.find("p", class_="css-ijz3vq")
        name_text = name_el.get_text(strip=True) if name_el else ""
        link_el = card.find("a", class_="css-15jfzpq")
        link = link_el.get("href", "") if link_el else ""
        if not link:
            continue
        if link and not link.startswith("http"):
            link = CHIZHIK_URL + link.split("?")[0]
        price_rub_el = card.find(class_="css-gl8r4y")
        price_rub_text = price_rub_el.get_text(strip=True).replace('\xa0', '') if price_rub_el else None
        price_kopeek_el = card.find(class_="css-h1dtet")
        price_kopeek_text = price_kopeek_el.get_text(strip=True) if price_kopeek_el else None
        price_text = price_rub_text + "." + price_kopeek_text if price_rub_text and price_kopeek_text else None
        discount_rub_el = card.find(class_="css-1x53jpj")
        discount_rub_text = discount_rub_el.get_text(strip=True).replace('\xa0', '') if discount_rub_el else None
        discount_kopeek_el = card.find(class_="css-t7jqfn")
        discount_kopeek_text = discount_kopeek_el.get_text(strip=True) if discount_kopeek_el else None
        discount_text = discount_rub_text + "." + discount_kopeek_text if discount_rub_text and discount_kopeek_text else None
        page_blocks[link] = [name_text, price_text, discount_text, article]
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
    driver = get_driver_no_images()
    time.sleep(1)
    conn = psycopg2.connect(DATABASE_URL)
    dixy_cats = [item for item in DIXY_FOOD_CATEGORIES_DICT.keys()]
    try:
        # shop = "Ашан"
        # for category in AUCHAN_FOOD_CATEGORIES_DICT.keys():
        #     cat_label = AUCHAN_FOOD_CATEGORIES_DICT[category]
        #     blocks = auchan_parse_category(category)
        #     if blocks:
        #         update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        # shop = "Лента"
        # for category in LENTA_FOOD_CATEGORIES_DICT.keys():
        #     cat_label = LENTA_FOOD_CATEGORIES_DICT[category]
        #     blocks = lenta_parse_category(category)
        #     if blocks:
        #         update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        # shop = "Чижик"
        # for category in CHIZHIK_FOOD_CATEGORIES_DICT.keys():
        #     cat_label = CHIZHIK_FOOD_CATEGORIES_DICT[category]
        #     blocks = chizhik_parse_category(category)
        #     if blocks:
        #         update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        shop = "Дикси"
        for category in DIXY_FOOD_CATEGORIES_DICT.keys():
            cat_label = DIXY_FOOD_CATEGORIES_DICT[category]
            blocks = dixy_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()

