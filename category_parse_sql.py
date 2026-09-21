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
from parse_qc import accept_or_discard
from dotenv import load_dotenv
import csv
import re
import uuid

load_dotenv()

DATE_FMT = "%Y-%m-%d"
DATABASE_URL = f"postgresql://postgres:{os.environ.get('SQL_PASSWORD')}@localhost:5432/price_monitoring"
CHROMIUM_VERSION = int(os.getenv('CHROMIUM_VERSION'))

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
# fn:492876 | fn:262929_1 | fn:date160520221455_206028_3 → article before trailing _N suffix
AUCHAN_ARTICLE_FN_REGEX = re.compile(r"/fn:(?:date\d+_)?(\d+)(?:_\d+)?/")
AUCHAN_ARTICLE_UNDERSCORE_REGEX = re.compile(r"_(\d+)_")

VKUSVIL_URL = "https://vkusvill.ru"
VKUSVIL_KEY_ELEMENT = "ProductCard__price"

CHIZHIK_URL = "https://chizhik.club"

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')

proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"

def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_1"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

def get_driver_proxy():
    options = uc.ChromeOptions()
    user_data_dir = r"D:\VS Project\price-monitoring\chrome_profile_1"
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
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".main-price .view-price-rubles"))
    )
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all("ul", class_=LENTA_PAGINATION_ELEMENT)
    last_page = 1
    if pages:
        for page in pages:
            raw_value = page.get_text(strip=True, separator=",")
            last_page = int(raw_value.split(",")[-1])
    blocks = {}
    print(url)
    page_blocks = lenta_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    base_url = url.rstrip("/")
    for page in range(2, last_page + 1):
        url = f"{base_url}/page/{page}/"
        print(url)
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".main-price .view-price-rubles"))
        )
        html = driver.page_source
        try:
            page_blocks = lenta_parse_category_page(html)
        except TimeoutException:
            continue
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def lenta_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    card_container = soup.select(LENTA_CARD_CONTAINER)
    try:
        cards = card_container[0].find_all("div", class_="lu-grid__item")
    except Exception as e:
        print(f"Lenta parse category page error: {e}")
        return page_blocks
    for card in cards:
        article = None
        name_el = card.find("span", class_="card-name_content")
        name_appendix_el = card.find("p", class_="card-name_package")
        name_text = name_el.get_text(strip=True) if name_el else ""
        name_appendix_text = name_appendix_el.get_text(strip=True) if name_appendix_el else ""
        name_text = f"{name_text} {name_appendix_text}".strip()
        link_el = card.find("a", class_="product-card")
        link = link_el.get("href", "") if link_el else ""
        price_el = card.find("span", class_="main-price")
        price_rubles_el = price_el.find("span", class_="view-price-rubles") if price_el else None
        price_kopecks_el = price_el.find("span", class_="view-price-kopecks") if price_el else None
        price_text = None
        if price_rubles_el:
            price_rubles = re.sub(r"\D", "", price_rubles_el.get_text())
            price_kopecks = re.sub(r"\D", "", price_kopecks_el.get_text()) or "00"
            price_text = (f"{price_rubles}.{price_kopecks.zfill(2)}")
        discount_el = card.find("span", class_="discount-badge")
        if link:
            article = str(link.split("-")[-1].split("/")[0]).zfill(6)
        old_price_text = None
        if discount_el:
            old_price_el = card.find("div", class_="old-price-product")
            old_price_rubles_el = old_price_el.find("span", class_="view-price-rubles") if old_price_el else None
            old_price_kopecks_el = old_price_el.find("span", class_="view-price-kopecks") if old_price_el else None
            if old_price_rubles_el:
                old_price_rubles = re.sub(r"\D", "", old_price_rubles_el.get_text())
                old_price_kopecks = re.sub(r"\D", "", old_price_kopecks_el.get_text()) or "00"
                old_price_text = (f"{old_price_rubles}.{old_price_kopecks.zfill(2)}")
        if not accept_or_discard(link, name_text, price_text, article, "Лента"):
            continue
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
        time.sleep(1)
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

def extract_auchan_article(card) -> str | None:
    """Article lives in imgproxy `/fn:492876/`; older cards used `_492876_` in the filename."""
    srcs = []
    imgs = card.find_all("img")
    picture_imgs = [
        img for img in imgs
        if img.get("class") and any("styles_picture_img" in cls for cls in img.get("class", []))
    ]
    for img in picture_imgs or imgs:
        for attr in ("src", "data-src", "srcset"):
            val = img.get(attr)
            if val:
                srcs.append(val)
    blob = " ".join(srcs)
    match = AUCHAN_ARTICLE_FN_REGEX.search(blob) or AUCHAN_ARTICLE_UNDERSCORE_REGEX.search(blob)
    if not match:
        return None
    return match.group(1).zfill(6)


def auchan_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(AUCHAN_ITEM_CARD_CONTAINER)
    for card in cards:
        article = extract_auchan_article(card)
        name_el = card.find(class_=AUCHAN_ITEM_CARD_NAME_CLASS)
        name_text = name_el.get_text(strip=True) if name_el else ""
        link_el = card.find("a", class_=AUCHAN_ITEM_CARD_LINK_CLASS)
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = AUCHAN_URL + link.split("?")[0]
        price_el = card.find(class_=AUCHAN_ITEM_CARD_PRICE_CLASS)
        price_text = price_el.get_text(strip=True).replace("₽", "").replace(",", ".") if price_el else None
        discount_el = card.find(class_=AUCHAN_ITEM_CARD_BEFORE_DISCOUNT_CLASS)
        discount_text = discount_el.get_text(strip=True).replace("₽", "").replace(",", ".") if discount_el else None
        if not accept_or_discard(link, name_text, price_text, article, "Ашан"):
            continue
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
        if not accept_or_discard(link, name_text, price_text, article, "Чижик"):
            continue
        page_blocks[link] = [name_text, price_text, discount_text, article]
    return page_blocks

def vkusvill_parse_category(url: str) -> str:
    driver.get(url)
    wait_for_element(driver, VKUSVIL_KEY_ELEMENT)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all("a", class_="VV_Pager__Item")
    pages_text = [page.get_text(strip=True) for page in pages] if pages else None
    last_page = int(pages_text[-2]) if pages_text else 1
    blocks = {}
    page_blocks = vkusvill_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    for page in range(2, last_page + 1):
        time.sleep(1)
        url = f"{url}?PAGEN_1={page}"
        driver.get(url)
        wait_for_element(driver, VKUSVIL_KEY_ELEMENT)
        url = url.split("?")[0]
        html = driver.page_source
        page_blocks = vkusvill_parse_category_page(html)
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def vkusvill_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find("div", class_="ProductCards__list")
    for card in cards.find_all(recursive=False):
        article_el = card.find("div", class_="js-datalayer-catalog-list-item")
        if not article_el:
            continue
        article = str(article_el.get("data-id", "")).zfill(6) if article_el else None
        img_el = card.find("img")
        name_text = img_el.get("title", "").strip().replace("\xa0", " ") if img_el else ""
        link_el = card.find("a")
        raw_link = link_el.get("href", "") if link_el else ""
        link = VKUSVIL_URL + raw_link if raw_link else ""
        price_el = card.find("span", class_="js-datalayer-catalog-list-price")
        old_price_el = card.find("span", class_="js-datalayer-catalog-list-price-old")
        price_text = price_el.get_text(strip=True) if price_el else None
        discount_text = old_price_el.get_text(strip=True) if old_price_el else None
        print(link, name_text, price_text, discount_text, article)
        if not accept_or_discard(link, name_text, price_text, article, "Вкусвилл"):
            continue
        page_blocks[link] = [name_text, price_text, discount_text, article]
    exit()
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
    driver.get("https://google.com")
    time.sleep(2)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        shop = "Ашан"
        for category in AUCHAN_FOOD_CATEGORIES_DICT.keys():
            cat_label = AUCHAN_FOOD_CATEGORIES_DICT[category]
            blocks = auchan_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        shop = "Лента"
        for category in LENTA_FOOD_CATEGORIES_DICT.keys():
            cat_label = LENTA_FOOD_CATEGORIES_DICT[category]
            blocks = lenta_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        shop = "Вкусвилл"
        for category in VKUSVIL_FOOD_CATEGORIES_DICT.keys():
            cat_label = VKUSVIL_FOOD_CATEGORIES_DICT[category]
            blocks = vkusvill_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
        driver.quit()
        driver = get_driver_proxy()
        driver.get("https://google.com")
        shop = "Чижик"
        for category in CHIZHIK_FOOD_CATEGORIES_DICT.keys():
            cat_label = CHIZHIK_FOOD_CATEGORIES_DICT[category]
            blocks = chizhik_parse_category(category)
            if blocks:
                update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    finally:
        conn.close()
        driver.quit()

