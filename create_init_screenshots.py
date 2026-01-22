import undetected_chromedriver as uc
from datetime import datetime
from product_list import *
import os
import time

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--disable-cache')
    options.add_argument('--disable-application-cache')
    options.add_argument('--disable-gpu-shader-disk-cache')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--clear-token-service')
    options.add_argument('--disable-background-networking')
    driver = uc.Chrome(options=options)
    driver.delete_all_cookies()
    return driver

def create_init_screenshots():
    driver = get_driver()
    os.makedirs(f"saved_pages/Initial_{datetime.now().strftime('%Y-%m-%d')}", exist_ok=True)
    for dict in [LENTA_PRODUCT_LIST_DICT, VKUSVIL_PRODUCT_LIST_DICT, PEREKRESTOK_PRODUCT_LIST_DICT, DIXY_PRODUCT_LIST_DICT, PYATEROCHKA_PRODUCT_LIST_DICT, AUCHAN_PRODUCT_LIST_DICT]:
            for product_name, product_url in dict.items():
                driver.get(product_url)
                time.sleep(1)
                save_page_as_screenshot(driver, product_name)
    driver.quit()

def save_page_as_screenshot(driver, filename='page', date=datetime.now().strftime('%Y-%m-%d')):
    try:
        driver.save_screenshot(f"saved_pages/Initial_{date}/{filename}_{date}.png")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pass

if __name__ == "__main__":
    create_init_screenshots()