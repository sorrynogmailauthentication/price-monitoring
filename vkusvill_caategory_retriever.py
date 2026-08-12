from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import os
import time


def get_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    return driver


def get_html(url, driver):
    driver.get(url)
    time.sleep(1)
    return driver.page_source


url = """https://vkusvill.ru/goods/"""
page = "https://vkusvill.ru"
driver = get_driver()
html = get_html(url, driver)
print(html[:20])
driver.quit()
soup = BeautifulSoup(html, "html.parser")
results = {}
# pick the ul you need (first ul shown here)
uls = soup.find_all("ul")
ul = uls[1]
if ul:
    for li in ul.find_all("li", recursive=False):  # direct li under this ul
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "").strip()
        href = page + href
        spans = a.find_all("span")
        second_span_text = spans[1].get_text(strip=True).replace("\xa0", " ") if len(spans) > 1 else None
        results[href] = second_span_text

print(results)