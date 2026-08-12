import time
import requests
from selenium.webdriver.common.by import By
from selenium import webdriver
import gspread
from google.oauth2.service_account import Credentials

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "mistral"
LINK_COL_NAME = "Link"
TARGET_COLS = ["Company", "Position", "Location", "Requirements"]
TABLE_NAME = "Volchek_Job_Search"
SHEET_NAME = "2"
# Укажите нужный URL-адрес

scopes = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

# Открываем таблицу (укажите точное название вашей таблицы)
sheet = client.open(TABLE_NAME).worksheet(SHEET_NAME)

print("Запуск проверки строк...")

headers = sheet.row_values(1)

def get_driver():
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    return driver

def get_content_from_url_linkedin(url):
    driver = get_driver()
    driver.get(url)
    time.sleep(1)
    findByClass = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']")
    textspan = findByClass.get_attribute("content")
    text = textspan.replace(" hiring ", "|").replace(" in ", "|").replace("| LinkedIn", "").replace(", Israel", "").strip()
    text_tuple = text.split("|")
    show_more = driver.find_element(By.CLASS_NAME, "show-more-less-html__markup")
    full_text = show_more.get_attribute("textContent").strip()
    requirements_text = get_job_requirements_mistral(full_text)
    text_tuple.append(requirements_text)
    return text_tuple

def get_job_requirements_mistral(page_content) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts job requirements from a job description"
                "As input, you will be given the HTML of a job description page. "
                "You need to find specific block that contain job requirements, usually it is called 'Job Requirements' or 'Requirements' or such"
                "Once you identified this block - list out in bullet points the job requirements"
                "Omit generalities unrelated to programming languages, technologies, frameworks, databases, years of experience, etc."
                "Truncate any long descriptive sentences with little substance"
                "truncate similar requirements into 1 bullet point"
                "Dont include any other text in your response, only the bullet points"
                "Dont use natural language in you response"
            },
            {"role": "user", "content": f"find job requirements in the following HTML: {page_content}"},
        ],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "").strip()

try:
    link_col_idx = headers.index(LINK_COL_NAME) + 1
    # Создаем список индексов для целевых столбцов
    target_indices = [headers.index(name) + 1 for name in TARGET_COLS]
except ValueError as e:
    print(f"Ошибка: Один из указанных заголовков не найден в таблице! {e}")
    exit()

all_rows = sheet.get_all_values()
# Перебираем строки. Начинаем со 2-й строки (индекс 1 в Python), чтобы пропустить заголовки
for index, row in enumerate(all_rows[1:], start=2):
    # Если строка пустая, пропускаем её
    if not row:
        continue
        
    url = row[link_col_idx - 1].strip() if len(row) >= link_col_idx else ""
    
    first_target_idx = target_indices[0] - 1
    is_target_empty = len(row) < target_indices[0] or row[first_target_idx].strip() == ""
    
    
    if url.startswith("http") and is_target_empty and "linkedin" in url:
        print(f"Обработка строки {index}: {url}")
        
        # 2. Вызываем вашу функцию, передавая ссылку
        result_tuple = get_content_from_url_linkedin(url)
        
        cells_to_update = []
        for i, val in enumerate(result_tuple):
            col_num = target_indices[i]
            cells_to_update.append(gspread.cell.Cell(row=index, col=col_num, value=val))
            
        # Обновляем все ячейки этой строки за один запрос
        sheet.update_cells(cells_to_update)
        sheet_id = sheet._properties['sheetId']
        sheet.spreadsheet.batch_update({
            "requests": [{
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": index - 1, "endIndex": index},
                    "properties": {"pixelSize": 21},
                    "fields": "pixelSize"
                }
            }]
        })
        
        print(f"Строка {index} успешно заполнена: {result_tuple}")
        
        # Небольшая пауза, чтобы не превысить лимиты запросов к Google API
        time.sleep(1) 

print("Обработка всех новых строк завершена!")
