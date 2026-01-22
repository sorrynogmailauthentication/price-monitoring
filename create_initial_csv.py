import csv
from product_list import *


def create_csv_from_all_dicts(filename='all_products.csv'):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Product Name', 'Product URL'])
        for dict in [LENTA_PRODUCT_LIST_DICT, VKUSVIL_PRODUCT_LIST_DICT, PEREKRESTOK_PRODUCT_LIST_DICT, DIXY_PRODUCT_LIST_DICT, PYATEROCHKA_PRODUCT_LIST_DICT, AUCHAN_PRODUCT_LIST_DICT]:
            for product_name, product_url in dict.items():
                writer.writerow([product_name, product_url])
    print(f"CSV file '{filename}' created with {len(LENTA_PRODUCT_LIST_DICT) + len(VKUSVIL_PRODUCT_LIST_DICT) + len(PEREKRESTOK_PRODUCT_LIST_DICT) + len(DIXY_PRODUCT_LIST_DICT) + len(PYATEROCHKA_PRODUCT_LIST_DICT) + len(AUCHAN_PRODUCT_LIST_DICT)} products!")

if __name__ == "__main__":
    create_csv_from_all_dicts('all_products.csv')