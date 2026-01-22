import undetected_chromedriver as uc
import time
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
PEREKRESTOK_PRICE_ELEMENT = 'price-card-unit-value'
PEREKRESTOK_PRICE_REGEX = r'\d+,\d{2}'
PEREKRESTOK_PRODUCT_LIST_URLS = [
    "https://www.perekrestok.ru/cat/107/p/ris-mistral-zasmin-belyj-aromatnyj-dlinnozernyj-500g-39747",
    "https://www.perekrestok.ru/cat/107/p/ris-mistral-kuban-belyj-kruglozernyj-900g-3766",
    "https://www.perekrestok.ru/cat/107/p/grecka-mistral-900g-53673"
]
PEREKRESTOK_PRODUCT_LIST_PRICES = []
DIXY_PRODUCT_LIST_URLS = [
    "https://dixy.ru/product/ris-natsional-srednezernyy-dlya-plova-900g-2000274400/",
    "https://dixy.ru/product/ris-zernyshko-k-zernyshku-proparennyy-5kh80g-400g-2000310624/",
    "https://dixy.ru/product/ris-zernyshko-k-zernyshku-kruglozernyy-900g-2000180350/"
]
DIXY_PRODUCT_LIST_PRICES = []
DIXY_PRICE_REGEX = r'\d+\.\d{2}'
DIXY_PRICE_ELEMENT = 'card__price-num'
PYATEROCHKA_PRODUCT_LIST_URLS = [
    "https://5ka.ru/product/fasol-konservirovannaya-bondyuel-belaya-v-tomatnom--39419/",
    "https://5ka.ru/product/tomaty-cherri-global-village-selection-chernye-250--4374015/",
    "https://5ka.ru/product/batonchik-snickers-super-shokoladnyy-s-karamelyu-a--4133363/"
]
PYATEROCHKA_PRODUCT_LIST_PRICES = []
PYATEROCHKA_PRICE_REGEX = r'\d+\.\d{2}'
PYATEROCHKA_PRICE_ELEMENT = 'price-card-unit-value'
AUCHAN_PRODUCT_LIST_URLS = [
    "https://www.auchan.ru/product/moloko-domik-v-derevne-ultrapasterizovannoe-3-5-950-g/",
    "https://www.auchan.ru/product/moloko-pasterizovannoe-selo-zelenoe-3-2-2-l/",
    "https://www.auchan.ru/product/moloko-past-3-2-955g-dvd-bzmzh/"
]
AUCHAN_PRODUCT_LIST_PRICES = [
    
]
AUCHAN_PRICE_REGEX = r'\d+\,\d{2}'
AUCHAN_PRICE_ELEMENT = 'styles_price'



def get_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    return driver

def get_auchan_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//div[starts-with(@class, '{AUCHAN_PRICE_ELEMENT}')]")
        price_text = price_element.text
        price_match = re.search(AUCHAN_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
        else:
            price = "Achan wrong pattern"
            print("Achan price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "Achan error"
    finally:
        return price

def get_pyaterochka_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_elements = driver.find_elements(By.XPATH, "//meta[@itemprop='price']")
        if len(price_elements) >= 2:
            price_text = price_elements[1].get_attribute('content')
        elif len(price_elements) == 1:
            price_text = price_elements[0].get_attribute('content')
        price_match = re.search(PYATEROCHKA_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group())
        else:
            price = "Pyaterochka wrong pattern"
            print("Pyaterochka price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "Pyaterochka error"
    finally:
        return price


def get_dixy_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_element = driver.find_element(By.CLASS_NAME, DIXY_PRICE_ELEMENT)
        price_text = price_element.get_attribute('textContent')
        price_match = re.search(DIXY_PRICE_REGEX, price_text)
        if price_match:
            price = round(float(price_match.group()), 2)
        else:
            price = "Dixy wrong pattern"
            print("Dixy price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "Dixy error"
    finally:
        return price


def get_perekrestok_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//div[starts-with(@class, '{PEREKRESTOK_PRICE_ELEMENT}')]")
        price_text = price_element.text
        price_match = re.search(PEREKRESTOK_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
        else:
            price = "Perekrestok wrong pattern"
            print("Perekrestok price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "Perekrestok error"
    finally:
        return price

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
        else:
            price = "Lenta wrong pattern"
            print("Lenta price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "Lenta error"
    finally:
        return price


def get_vkusvil_price(url, driver):
    price = None
    try:
        driver.get(url)
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//span[starts-with(@class, '{VKUSVIL_PRICE_ELEMENT}')]")
        price_text = price_element.text
        price_match = re.search(r'\d+', price_text)
        if price_match:
            price = round(float(price_match.group()), 2)
            print(price)
        else:
            price = "VKUSVIL wrong pattern"
            print("VKUSVIL price pattern not found")
    except Exception as e:
        print(f"Error: {e}")
        price = "VKUSVIL error"
    finally:
        return price

if __name__ == "__main__":

    driver = get_driver()
    # for url in LENTA_PRODUCT_LIST_URLS:
    #     price = get_lenta_price(url, driver)
    #     LENTA_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    # for url in VKUSVIL_PRODUCT_LIST_URLS:
    #     price = get_vkusvil_price(url, driver)
    #     VKUSVIL_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    # for url in PEREKRESTOK_PRODUCT_LIST_URLS:
    #     price = get_perekrestok_price(url, driver)
    #     PEREKRESTOK_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    # for url in DIXY_PRODUCT_LIST_URLS:
    #     price = get_dixy_price(url, driver)
    #     DIXY_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    # for url in PYATEROCHKA_PRODUCT_LIST_URLS:
    #     price = get_pyaterochka_price(url, driver)
    #     PYATEROCHKA_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    # for url in AUCHAN_PRODUCT_LIST_URLS:
    #     price = get_auchan_price(url, driver)
    #     AUCHAN_PRODUCT_LIST_PRICES.append(price)
    #     time.sleep(3)
    print(get_pyaterochka_price("https://5ka.ru/product/makarony-barilla-spagetti-n-5-450g--4037644", driver))
    driver.quit()
    print(LENTA_PRODUCT_LIST_PRICES)
    print(VKUSVIL_PRODUCT_LIST_PRICES)
    print(PEREKRESTOK_PRODUCT_LIST_PRICES)
    print(DIXY_PRODUCT_LIST_PRICES)
    print(PYATEROCHKA_PRODUCT_LIST_PRICES)
    print(AUCHAN_PRODUCT_LIST_PRICES)