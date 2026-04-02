from datetime import datetime
from category_parse_sql import *

if __name__ == "__main__":
    today = datetime.now().strftime(DATE_FMT)
    driver = get_driver_no_images()
    time.sleep(1)
    blocks = lenta_parse_category("https://lenta.com/catalog/ovoshchi-frukty-144/")
    blocks = auchan_parse_category("https://www.auchan.ru/catalog/ptica-myaso/")
    blocks = dixy_parse_category("https://dixy.ru/catalog/ovoshchi-frukty/")
    if blocks:
        test_write_to_csv(blocks)
    lenta_blocks = {}
    for category in LENTA_FOOD_CATEGORIES_DICT.keys():
        blocks = lenta_parse_category(category)
        if blocks:
            lenta_blocks.update(blocks)
    test_write_to_csv(lenta_blocks, "lenta_test.csv")
    auchan_blocks = {}
    for category in AUCHAN_FOOD_CATEGORIES_DICT.keys():
        blocks = auchan_parse_category(category)
        if blocks:
            auchan_blocks.update(blocks)
    test_write_to_csv(auchan_blocks, "aucha_test.csv")
    dixy_blocks = {}
    for category in DIXY_FOOD_CATEGORIES_DICT.keys():
        blocks = dixy_parse_category(category)
        if blocks:
            dixy_blocks.update(blocks)
    test_write_to_csv(dixy_blocks, "dixy_test.csv")
    driver.quit()