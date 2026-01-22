import undetected_chromedriver as uc
import time
import json
from bs4 import BeautifulSoup
import re

LENTA_PRICE_REGEX = r'\d+,\d{2}'
LENTA_PRICE_ELEMENT = 'main-price title-28-20'
LENTA_PRODUCT_LIST_URLS = [
    "https://lenta.com/product/krupa-grechnevaya-yadrica-vs-rossiya-900g-014384/",
    "https://lenta.com/product/muka-vs-rossiya-2kg-073015/",
    "https://lenta.com/product/drozhzhi-moment-hlebopekarnye-suhie-bystrodejjstv-rossiya-11g-23638/"
    ]
LENTA_PRODUCT_LIST_PRICES = []

def get_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    return driver

def get_lenta_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        html = driver.page_source
        body_index = html.find('<body>')
        html_body = html[body_index:] if body_index != -1 else html
        search_text = LENTA_PRICE_ELEMENT
        index = html_body.find(search_text)
        if index != -1:
            html_price_snippet = html_body[index:index + 100]
            price_match = re.search(LENTA_PRICE_REGEX, html_price_snippet)
            if price_match:
                price = float(price_match.group().replace(',', '.'))
                print(price)
            else:
                price = "wrong pattern`"
                print("Lenta price pattern not found")
        else:
            price = "wrong element"
            print("Lenta price element not found")
    except Exception as e:
        print(f"Error: {e}")
        pass
    finally:
        return price

# Example usage
if __name__ == "__main__":

    driver = get_driver()
    for url in LENTA_PRODUCT_LIST_URLS:
        price = get_lenta_price(url, driver)
        LENTA_PRODUCT_LIST_PRICES.append(price)
        time.sleep(3)
    driver.quit()
    print(LENTA_PRODUCT_LIST_PRICES)