import pandas as pd
import os
from product_list import *


def update_products_csv(filename='all_products.csv'):
    all_products = {}
    for dict in [LENTA_PRODUCT_LIST_DICT, VKUSVIL_PRODUCT_LIST_DICT, PEREKRESTOK_PRODUCT_LIST_DICT, 
                 DIXY_PRODUCT_LIST_DICT, PYATEROCHKA_PRODUCT_LIST_DICT, AUCHAN_PRODUCT_LIST_DICT]:
        all_products.update(dict)
    
    # Read existing file or create new
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename, encoding='utf-8-sig')
        
        # Get existing URLs
        existing_urls = set(df_existing['Product URL'].tolist())
        
        # Find new products
        new_products = []
        for product_name, product_url in all_products.items():
            if product_url not in existing_urls:
                new_products.append({'Product Name': product_name, 'Product URL': product_url})
        
        if new_products:
            # Add new products
            df_new = pd.DataFrame(new_products)
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)
            df_updated.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Added {len(new_products)} new products!")
            print(f"Total: {len(df_updated)} products")
        else:
            print(f"No new products. Total: {len(df_existing)} products")
    else:
        pass

if __name__ == "__main__":
    update_products_csv('all_products.csv')