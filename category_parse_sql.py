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



load_dotenv()

CARD_CONTAINER = "div[data-testid='productCard-container']"
LENTA_CARD_CONTAINER = "div[class='lu-grid']"
NAME_CLASS = "styles_productCardContentPanel_name__gtZfG"
PRICE_CLASS = "styles_price__U1y_f"
DISCOUNT_CLASS = "styles_price__oldPrice__VsVTT"
PAGINATION_ITEM_CLASS = "styles_paginationItem__eSg3p"
AUCHAN_PRICE_REGEX = r'\d+\,\d{2}'
AUCHAN_PRICE_ELEMENT = 'styles_price'
AUCHAN_URL = "https://www.auchan.ru/"
LENTA_URL = "https://lenta.com/"
CATEGORY_PAGES_ELEMENT = "styles_paginationItem__eSg3p"
CATEGORIES_SECTION_ELEMENT = "styles_youMayNeed___gUus"
DATE_FMT = "%Y-%m-%d"
DATABASE_URL = f"postgresql://postgres:{os.environ.get('SQL_PASSWORD')}@localhost:5432/price_monitoring"


CHROMIUM_VERSION = 145

def get_driver():
    options = uc.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}  # 2 = do not load images
    options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

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
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "main-price")))
    except TimeoutException:
        pass
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all("ul", class_="pagination-nav__list")
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
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "main-price")))
        except TimeoutException:
            continue
        time.sleep(0.5)
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
    card_container = soup.select(LENTA_CARD_CONTAINER)
    cards = card_container[0].find_all("div", class_="lu-grid__item")
    for card in cards:
        name_el = card.find("span", class_="card-name_content")
        name_appendix_el = card.find("p", class_="card-name_package")
        name_text = name_el.get_text(strip=True) if name_el else ""
        name_appendix_text = name_appendix_el.get_text(strip=True) if name_appendix_el else ""
        name_text = f"{name_text} {name_appendix_text}"
        link_el = card.find("a", class_="product-card")
        link = link_el.get("href", "") if link_el else ""
        price_el = card.find("span", class_="main-price")
        price_text = price_el.get_text(strip=True).replace("₽", "").replace("\xa0", "") if price_el else None
        discount_el = card.find("span", class_="discount-badge")
        if discount_el:
            old_price_el = card.find("div", class_="old-price")
            old_price_text = old_price_el.get_text(strip=True).replace("₽", "").replace("\xa0", "").split("-")[0] if old_price_el else None
        else:
            old_price_text = None
        page_blocks[link] = [name_text, price_text, old_price_text]
    return page_blocks

def auchan_parse_category(url: str) -> str:
    driver.get(url)
    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(1)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all(class_=lambda c: c and CATEGORY_PAGES_ELEMENT in " ".join(c) if isinstance(c, list) else CATEGORY_PAGES_ELEMENT in str(c))
    last_page = 1
    if pages:
        for page in pages:
            value = page.get_text(strip=True)
            if value and int(value) > last_page:
                last_page = int(value)
    blocks = {}
    page_blocks = auchan_parse_category_page(html)
    if page_blocks:
        blocks.update(page_blocks)
    for page in range(2, last_page + 1):
        url = f"{url}?page={page}"
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            continue
        time.sleep(0.5)
        html = driver.page_source
        page_blocks = auchan_parse_category_page(html)
        url = url.split("?")[0]
        if page_blocks:
            blocks.update(page_blocks)
        else:
            break
    return blocks

def auchan_parse_category_page(html: str) -> str:
    page_blocks = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(CARD_CONTAINER)
    for card in cards:
        name_el = card.find(class_=lambda c: c and NAME_CLASS in " ".join(c) if isinstance(c, list) else NAME_CLASS in str(c))
        name_text = name_el.get_text(strip=True) if name_el else ""
        link_el = card.find("a", class_=lambda c: c and "styles_productCardContentPanel_link" in " ".join(c) if isinstance(c, list) else "styles_productCardContentPanel_link" in str(c))
        if not link_el:
            link_el = card.find("a", href=lambda h: h and "/product/" in h)
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = AUCHAN_URL + link.split("?")[0]
        price_el = card.find(class_=lambda c: c and PRICE_CLASS in " ".join(c) and "oldPrice" not in " ".join(c) if isinstance(c, list) else PRICE_CLASS in str(c) and "oldPrice" not in str(c))
        price_text = price_el.get_text(strip=True).replace("₽", "") if price_el else None
        discount_el = card.find(class_=lambda c: c and DISCOUNT_CLASS in " ".join(c) if isinstance(c, list) else DISCOUNT_CLASS in str(c))
        discount_text = discount_el.get_text(strip=True) if discount_el else None
        page_blocks[link] = [name_text, price_text, discount_text]
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
        for url, (name, price_text, discount_text) in blocks.items():
            # Upsert product
            cur.execute(
                """
                INSERT INTO products (url, product_name, shop, category)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    shop = EXCLUDED.shop,
                    category = EXCLUDED.category
                """,
                (url, name or None, shop, cat_label),
            )
            # Upsert price for today
            price_num = _parse_price(price_text)
            cur.execute(
                """
                INSERT INTO prices (product_url, date, price, discount)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_url, date) DO UPDATE SET
                    price = EXCLUDED.price,
                    discount = EXCLUDED.discount
                """,
                (url, today, price_num, discount_text),
            )
    conn.commit()


if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver()
    driver.delete_all_cookies()
    time.sleep(1)
    blocks = lenta_parse_category("https://lenta.com/catalog/ovoshchi-frukty-144/")
    if blocks:
        with open("lenta_test.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Product Name", "Price", "Discount"])
            for url, (name, price, discount) in blocks.items():
                writer.writerow([url, name, price, discount])
    driver.quit()
    # conn = psycopg2.connect(DATABASE_URL)
    # try:
    #     shop = "Ашан"
    #     for category in AUCHAN_FOOD_CATEGORIES_DICT.keys():
    #         cat_label = AUCHAN_FOOD_CATEGORIES_DICT[category]
    #         blocks = auchan_parse_category(category)
    #         if blocks:
    #             update_or_append_products_sql(conn, blocks, today, shop, cat_label)
    # finally:
    #     conn.close()
    #     driver.quit()

