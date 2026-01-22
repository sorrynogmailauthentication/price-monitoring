import undetected_chromedriver as uc
import time
import json
from bs4 import BeautifulSoup
import re
from selenium.webdriver.common.by import By

LENTA_PRICE_REGEX = r'\d+,\d{2}'
LENTA_PRICE_ELEMENT = 'main-price title-28-20'
LENTA_PRODUCT_LIST_URLS = [
    "https://lenta.com/product/krupa-grechnevaya-yadrica-vs-rossiya-900g-014384/",
    "https://lenta.com/product/muka-vs-rossiya-2kg-073015/",
    "https://lenta.com/product/drozhzhi-moment-hlebopekarnye-suhie-bystrodejjstv-rossiya-11g-23638/"
    ]
LENTA_PRODUCT_LIST_PRICES = []
VKUSVIL_PRODUCT_LIST_URLS = [
    "https://vkusvill.ru/goods/ris-mistral-zhasmin-500-g-32687.html",
    "https://vkusvill.ru/goods/krupa-mannaya-makfa-iz-tverdykh-sortov-700-g-40587.html",
    "https://vkusvill.ru/goods/krupa-grechnevaya-makfa-yadritsa-v-paketikakh-400-g-40585.html"

]
VKUSVIL_PRODUCT_LIST_PRICES = []
VKUSVIL_PRICE_REGEX = r'\d+(?=&)'
VKUSVIL_PRICE_ELEMENT = 'Price Price--lg'

def get_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    return driver

def get_lenta_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//span[starts-with(@class, '{LENTA_PRICE_ELEMENT}')]")
        price_text = price_element.text
        price_match = re.search(LENTA_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
            print(price)
        else:
            price = "wrong pattern`"
            print("Lenta price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "error"
    finally:
        return price


def get_vkusvil_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        
        
        # Find element where class starts with "Price"
        price_element = driver.find_element(By.XPATH, f"//span[starts-with(@class, '{VKUSVIL_PRICE_ELEMENT}')]")
        price_text = price_element.text  # This includes ::before content
        
        # Extract digits using regex
        price_match = re.search(r'\d+', price_text)
        if price_match:
            price = float(price_match.group())
            print(price)
        else:
            price = "wrong pattern"
            print("VKUSVIL price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "error"
    finally:
        return price

# Example usage
if __name__ == "__main__":

    driver = get_driver()
    for url in LENTA_PRODUCT_LIST_URLS:
        price = get_lenta_price(url, driver)
        LENTA_PRODUCT_LIST_PRICES.append(price)
        time.sleep(3)
    for url in VKUSVIL_PRODUCT_LIST_URLS:
        price = get_vkusvil_price(url, driver)
        VKUSVIL_PRODUCT_LIST_PRICES.append(price)
        time.sleep(3)
    driver.quit()
    print(LENTA_PRODUCT_LIST_PRICES)
    print(VKUSVIL_PRODUCT_LIST_PRICES)