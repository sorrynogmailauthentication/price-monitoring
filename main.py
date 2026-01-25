import undetected_chromedriver as uc
import time
import re
from selenium.webdriver.common.by import By
from product_list import *
import pandas as pd
from datetime import datetime
import os
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

LENTA_PRICE_REGEX = r'\d+,\d{2}'
LENTA_PRICE_ELEMENT = 'main-price title-28-20'
VKUSVIL_PRICE_REGEX = r'\d+(?=&)'
VKUSVIL_PRICE_ELEMENT = 'Price Price--lg'
PEREKRESTOK_PRICE_ELEMENT = 'price-card-unit-value'
PEREKRESTOK_PRICE_REGEX = r'\d+,\d{2}'
DIXY_PRICE_REGEX = r'\d+\.\d{2}'
DIXY_PRICE_ELEMENT = 'card__price-num'
PYATEROCHKA_PRICE_REGEX = r'\d+\.\d{2}'
PYATEROCHKA_PRICE_ELEMENT = 'price-card-unit-value'
AUCHAN_PRICE_REGEX = r'\d+\,\d{2}'
AUCHAN_PRICE_ELEMENT = 'styles_price'

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.page_load_strategy = 'eager'
    driver = uc.Chrome(options=options)
    return driver

def save_page_as_screenshot(driver, filename, directory):
    try:
        driver.save_screenshot(f"{directory}/{filename}_{datetime.now().strftime('%Y-%m-%d')}.png")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pass

def get_auchan_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//div[starts-with(@class, '{AUCHAN_PRICE_ELEMENT}')]")
        if not price_element:
            price = "Achan price element not found"
            raise Exception(price)
        price_text = price_element.text
        price_match = re.search(AUCHAN_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
        else:
            price = "Achan wrong pattern"
    except TimeoutException:
        price = "Achan page load timeout"
    except Exception:
        price = f"Achan error"
    finally:
        return price

def get_pyaterochka_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1.2)
        price_elements = driver.find_elements(By.XPATH, "//meta[@itemprop='price']")
        if not price_elements:
            not_in_stock = driver.find_element(By.XPATH, "//span//h2[contains(text(), 'Нет в наличии')]")
            if not_in_stock:
                raise ValueError("Not in stock")
            raise ValueError("Pyaterochka price element not found")
        if len(price_elements) >= 2:
            price_text = price_elements[1].get_attribute('content')
        elif len(price_elements) == 1:
            price_text = price_elements[0].get_attribute('content')
        price_match = re.search(PYATEROCHKA_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group())
        else:
            price = "Pyaterochka wrong pattern"
    except TimeoutException:
        price = "Pyaterochka page load timeout"
    except ValueError as e:
        price = e.args[0]
    except Exception:
        price = f"Pyaterochka error"
    finally:
        return price

def get_dixy_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)
        price_element = driver.find_element(By.CLASS_NAME, DIXY_PRICE_ELEMENT)
        if not price_element:
            raise ValueError()
        price_text = price_element.get_attribute('textContent')
        price_match = re.search(DIXY_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group())
        else:
            price = "Dixy wrong pattern"
    except TimeoutException:
        price = "Dixy page load timeout"
    except ValueError:
        price = "Dixy price element not found"
    except Exception:
        price = f"Dixy error"
    finally:
        return price

def click_middle_right(driver):
    try:
        actions = ActionChains(driver)
        actions.reset_actions()
        window_width = driver.execute_script("return window.innerWidth")
        window_height = driver.execute_script("return window.innerHeight")
        x = int(window_width * 0.75)
        y = int(window_height * 0.5)
        actions.move_by_offset(x - window_width//2, y - window_height//2).click().perform()
        actions.reset_actions()
    except Exception as e:
        print(f"Error clicking middle right: {e}")
    finally:
        return None

def get_perekrestok_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        click_middle_right(driver)
        time.sleep(1)
        price_element = driver.find_element(By.XPATH, f"//div[starts-with(@class, '{PEREKRESTOK_PRICE_ELEMENT}')]")
        if not price_element:
            raise ValueError("Perekrestok price element not found")
        price_text = price_element.text
        price_match = re.search(PEREKRESTOK_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
        else:
            price = "Perekrestok wrong pattern"
    except TimeoutException:
        price = "Perekrestok page load timeout"
    except ValueError as e:
        price = e.args[0]
    except Exception:
        price = f"Perekrestok error"
    finally:
        return price

def get_lenta_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)
        price_elements = driver.find_elements(By.XPATH, f"//span[starts-with(@class, '{LENTA_PRICE_ELEMENT}')]")
        if not price_elements:
            not_in_stock = driver.find_elements(By.XPATH, "//p[@class='out-of-stock-goods']")
            if not_in_stock:
                raise ValueError("Not in stock")
            raise ValueError("Lenta price element not found")
        price_text = price_elements[0].text
        price_match = re.search(LENTA_PRICE_REGEX, price_text)
        if price_match:
            price = float(price_match.group().replace(',', '.'))
        else:
            price = "Lenta wrong pattern"
    except TimeoutException:
        price = "Lenta page load timeout"
    except ValueError as e:
        price = e.args[0]
    except Exception:
        price = f"Lenta error {e}"
    finally:
        return price


def get_vkusvil_price(url, driver):
    price = None
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(0.5)
        price_element = driver.find_element(By.XPATH, f"//span[starts-with(@class, '{VKUSVIL_PRICE_ELEMENT}')]")
        if not price_element:
            raise ValueError()
        price_text = price_element.text
        price_match = re.search(r'\d+', price_text)
        if price_match:
            price = price_match.group()
        else:
            price = "VKUSVIL wrong pattern"
    except TimeoutException:
        price = "VKUSVIL page load timeout"
    except ValueError:
        price = "VKUSVIL price element not found"
    except Exception:
        price = f"VKUSVIL error"
    finally:
        return price

if __name__ == "__main__":
    
    today = datetime.now().strftime('%Y-%m-%d')
    directory = f"saved_pages/{today}"
    os.makedirs(directory, exist_ok=True)
    filename = f'all_products.csv'
    df = pd.read_csv(filename, encoding='utf-8-sig')
    df[today] = ''
    today_index = df.columns.get_loc(today)
    last_col = df.columns[today_index - 1]
    driver = get_driver()
    driver.delete_all_cookies()
    time.sleep(2)
    for name, url in LENTA_PRODUCT_LIST_DICT.items():
        price = get_lenta_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price) and type(price) == float:
            save_page_as_screenshot(driver, f"LENTA_{name}", directory)
        time.sleep(0.5)
    for name, url in VKUSVIL_PRODUCT_LIST_DICT.items():
        price = get_vkusvil_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price):
            save_page_as_screenshot(driver, f"VKUSVIL_{name}", directory)
        time.sleep(0.5)
    for name, url in PEREKRESTOK_PRODUCT_LIST_DICT.items():
        price = get_perekrestok_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price) and type(price) == float:
            save_page_as_screenshot(driver, f"PEREKRESTOK_{name}", directory)
        time.sleep(0.5)
    for name, url in DIXY_PRODUCT_LIST_DICT.items():
        price = get_dixy_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price) and type(price) == float:
            save_page_as_screenshot(driver, f"DIXY_{name}", directory)
        time.sleep(0.5)
    for name, url in PYATEROCHKA_PRODUCT_LIST_DICT.items():
        price = get_pyaterochka_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price) and type(price) == float:
            save_page_as_screenshot(driver, f"PYATEROCHKA_{name}", directory)
        time.sleep(0.5)
    for name, url in AUCHAN_PRODUCT_LIST_DICT.items():
        price = get_auchan_price(url, driver)
        df.loc[df['Product URL'] == url, today] = price
        last_price_series = df.loc[df['Product URL'] == url, last_col]
        last_price = last_price_series.values[0]
        if str(last_price) != str(price) and type(price) == float:
            save_page_as_screenshot(driver, f"AUCHAN_{name}", directory)
        time.sleep(0.5)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    if os.path.exists(directory) and os.path.isdir(directory):
        if not os.listdir(directory):
            os.rmdir(directory)
    driver.quit()


