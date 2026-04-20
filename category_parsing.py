import undetected_chromedriver as uc
import time
import pandas as pd
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from categories import *

CARD_CONTAINER = "div[data-testid='productCard-container']"
NAME_CLASS = "styles_productCardContentPanel_name__gtZfG"
PRICE_CLASS = "styles_price__U1y_f"
DISCOUNT_CLASS = "styles_price__oldPrice__VsVTT"
PAGINATION_ITEM_CLASS = "styles_paginationItem__eSg3p"
AUCHAN_PRICE_REGEX = r'\d+\,\d{2}'
AUCHAN_PRICE_ELEMENT = 'styles_price'
AUCHAN_URL = "https://www.auchan.ru/"
CATEGORY_PAGES_ELEMENT = "styles_paginationItem__eSg3p"
CATEGORIES_SECTION_ELEMENT = "styles_youMayNeed___gUus"
EXCEL_PATH = "auchan_prices.xlsx"
DATE_FMT = "%Y-%m-%d"


CHROMIUM_VERSION = 147

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
        time.sleep(1)
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
            link = "https://www.auchan.ru" + link.split("?")[0]
        price_el = card.find(class_=lambda c: c and PRICE_CLASS in " ".join(c) and "oldPrice" not in " ".join(c) if isinstance(c, list) else PRICE_CLASS in str(c) and "oldPrice" not in str(c))
        price_text = price_el.get_text(strip=True).replace("₽", "") if price_el else None
        discount_el = card.find(class_=lambda c: c and DISCOUNT_CLASS in " ".join(c) if isinstance(c, list) else DISCOUNT_CLASS in str(c))
        discount_text = discount_el.get_text(strip=True) if discount_el else None
        page_blocks[link] = [name_text, price_text, discount_text]
    return page_blocks

def ensure_excel_columns(df: pd.DataFrame, today: str) -> pd.DataFrame:
    price_col = f"{today} price"
    disc_col = f"{today} discounted"
    if price_col not in df.columns:
        df[price_col] = None
    if disc_col not in df.columns:
        df[disc_col] = None
    return df

def update_or_append_products(df: pd.DataFrame, blocks: dict, today: str, category: str) -> pd.DataFrame:
    price_col = f"{today} price"
    disc_col = f"{today} discounted"
    df = ensure_excel_columns(df, today)
    for url, (name, price, discount) in blocks.items():
        mask = df["url"] == url
        if mask.any():
            df.loc[mask, price_col] = price
            df.loc[mask, disc_col] = discount
            df.loc[mask, "shop"] = AUCHAN_FOOD_CATEGORIES_DICT[category][0]
            df.loc[mask, "category"] = AUCHAN_FOOD_CATEGORIES_DICT[category][1]
        else:
            new_row = {"url": url, "Product name": name, price_col: price, disc_col: discount, "shop": AUCHAN_FOOD_CATEGORIES_DICT[category][0]
            , "category": AUCHAN_FOOD_CATEGORIES_DICT[category][1]}
            for c in df.columns:
                if c not in new_row:
                    new_row[c] = None
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    driver = get_driver()
    driver.delete_all_cookies()
    time.sleep(1)
    for category in AUCHAN_FOOD_CATEGORIES_DICT.keys():
        blocks = auchan_parse_category(category)
        if blocks:
            df = update_or_append_products(df, blocks, today, category)
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")
    driver.quit()
