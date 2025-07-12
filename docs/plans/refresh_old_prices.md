# Refresh Old Prices Plan

## Current Scraper Behavior

The scraper only updates **new products**:
- Gets all URLs from sitemap  
- Filters out existing URLs
- Only scrapes products not in database

## Required Solution

Scrape products that meet ANY of these criteria:
1. **New products** (not in our database)
2. **Changed products** (in sitemap but we have them)  
3. **Oldest N products** (longest time since last scrape)

### 1. Add tracking field
```python
# Add to SupplierProduct model
last_scraped = models.DateTimeField(auto_now=True)
```

### 2. Add class defaults
```python
# In BaseScraper
class BaseScraper:
    DEFAULT_REFRESH_LIMIT = 100  # Clear default for refresh cycle

# In specific scrapers (optional override)
class SteelAndTubeScraper(BaseScraper):
    DEFAULT_REFRESH_LIMIT = 50  # Supplier-specific limit
```

### 3. Replace filter logic in base.py line 127
```python
# Get all URLs from sitemap
sitemap_urls = set(product_urls)

# Get existing URLs we have
existing_urls = set(SupplierProduct.objects.filter(supplier=self.supplier).values_list("url", flat=True))

# New products (in sitemap, not in our DB)
new_urls = sitemap_urls - existing_urls

# Changed products (in both sitemap and our DB)
changed_urls = sitemap_urls & existing_urls

# Oldest N products we have (whether in sitemap or not)
refresh_limit = self.limit or self.DEFAULT_REFRESH_LIMIT
oldest_products = SupplierProduct.objects.filter(
    supplier=self.supplier
).order_by('last_scraped')[:refresh_limit]
oldest_urls = set(p.url for p in oldest_products)

# Final URL list: new + changed + oldest
product_urls = list(new_urls | changed_urls | oldest_urls)
```

### 4. Add command flag
```bash
python manage.py run_scrapers --refresh-old --limit 100
```

### 5. Schedule nightly
```python
def refresh_old_job():
    call_command('run_scrapers', '--refresh-old', '--limit', '100')
```

## Result
- Always scrapes new/changed products from supplier
- Plus oldest N products for systematic refresh
- 3000 products = 30 day cycle for stale products