import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import requests
from datetime import datetime, timedelta

today = datetime.today().date()
week_ago = today - timedelta(days=7)

def is_in_last_week(line: str) -> bool:
    d = datetime.strptime(line.strip(), "%Y %B %d").date()
    return week_ago <= d <= today

PRESS_RELEASES_SECTION_CLASS = "col-lg-12 loaded"
FOOTER_SECTION_CLASS = "about"
CHROMIUM_VERSION = 145



def get_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=CHROMIUM_VERSION)
    return driver

driver = get_driver()

def fetch_press_release_text(url: str) -> str:
    driver.get(url)
    time.sleep(1)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("div", class_="container-wp--centered-blog")
    return article.get_text(separator="\n", strip=True)

driver = get_driver()
driver.get("https://www.crowdstrike.com/en-us/press-releases/?lang=1")
time.sleep(1)
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")
parent = soup.find("div", class_="col-lg-12")
direct_children = parent.find_all(recursive=False)


OLLAMA_URL = "http://localhost:11434/api/chat"   # Ollama endpoint
MODEL = "mistral"                                # e.g. `ollama pull mistral` beforehand



def summarize_with_mistral(text: str) -> str:
    # Truncate to stay within context if needed
    text = text[:8000]

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system",
             "content": "You concisely summarize press releases. "
                        "Return a short headline and 3–5 bullet points."},
            {"role": "user",
             "content": f"Summarize this press release:\n\n{text}"}
        ],
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "").strip()


for child in direct_children:
    year  = child.get("cs-year")          # '2026'
    month = child.get("cs-month")         # 'February'
    day   = child.find("div", class_="day").get_text(strip=True)
    if is_in_last_week(f"{year} {month} {day}"):
        href = child.find("a").get("href")
        link = "https://www.crowdstrike.com" + href
        text = fetch_press_release_text(link)
        summary = summarize_with_mistral(text.split("About CrowdStrike")[0])
        print(summary)
        break



