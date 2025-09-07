#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobs_manager.settings')
sys.path.append('/Users/adrianwhite/jobs_manager_project/backend')
django.setup()

from apps.client.models import Client
from apps.quoting.models import SupplierPriceList, SupplierProduct

def main():
    print("=== DATABASE QUERY RESULTS ===\n")

    # Check total suppliers and recent ones
    total_suppliers = Client.objects.count()
    print(f'Total suppliers in database: {total_suppliers}')

    recent_suppliers = Client.objects.order_by('-id')[:5]  # Last 5 created
    print('\nMost recently created suppliers:')
    for supplier in recent_suppliers:
        print(f'  ID: {supplier.id}, Name: {supplier.name}')

    # Search for various patterns
    search_terms = ['vulcan', 'ullrich', 'aluminium', 'aluminum', 'flat bar', 'ua2737']
    for term in search_terms:
        suppliers = Client.objects.filter(name__icontains=term)
        if suppliers.exists():
            print(f'\nSuppliers containing "{term}":')
            for supplier in suppliers:
                print(f'  ID: {supplier.id}, Name: {supplier.name}')

    # Search for products with specific item codes from our extraction
    item_codes = ['UA2737', 'UA1155', 'UA1161', 'UA6054', 'UA1167']
    print(f'\nSearching for products with specific item codes:')
    for code in item_codes:
        products = SupplierProduct.objects.filter(item_no__icontains=code)
        if products.exists():
            print(f'  Products with item code containing "{code}": {products.count()}')
            for product in products[:2]:  # Show first 2
                print(f'    - {product.item_no}: {product.product_name} (${product.unit_price})')
        else:
            print(f'  No products found with item code containing "{code}"')

    # Check recent price lists
    recent_price_lists = SupplierPriceList.objects.order_by('-uploaded_at')[:3]
    print(f'\nMost recent price list uploads:')
    for pl in recent_price_lists:
        print(f'  ID: {pl.id}, Filename: {pl.file_name}, Supplier: {pl.supplier.name}, Uploaded: {pl.uploaded_at}')

        # Get products from this price list
        products = SupplierProduct.objects.filter(price_list=pl)
        print(f'  Products in this price list: {products.count()}')

        if products.exists():
            print('  Sample products:')
            for product in products[:3]:  # Show first 3
                print(f'    - {product.item_no}: {product.product_name} (${product.unit_price})')
            if products.count() > 3:
                print(f'    ... and {products.count() - 3} more')

    # Check total products
    total_products = SupplierProduct.objects.count()
    print(f'\nTotal products in database: {total_products}')

if __name__ == '__main__':
    main()