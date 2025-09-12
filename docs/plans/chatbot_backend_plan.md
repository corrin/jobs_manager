# Chatbot Backend Plan

## What we need:
- API endpoints for price/stock lookups
- API key authentication for the chatbot service

## Sample Conversation to Define Requirements

**User**: "I need to price 50 meters of 25x25x3mm steel angle for the Johnson job"

**Assistant**: "I found several options for 25x25x3mm steel angle:

**In Stock:**
- We have 45m available at $12.50/m (cost $8.30/m) - Location: Rack A3
- 23m at $11.80/m (cost $7.90/m) - Location: Yard

**Supplier Pricing:**
- Steel Solutions: 50m available at $7.20/m (6m lengths)
- Metro Steel: 100m+ available at $6.95/m (12m lengths)
- Aussie Steel: Out of stock, ETA 2 weeks

You need 50m total. Options:
1. Use our stock (45m + 23m = 68m available) - Mix of pricing
2. Order from Metro Steel - Best price, good lengths
3. Combine: Use 45m from stock + order 5m from Metro"

**User**: "What about 304 stainless instead?"

**Assistant**: "For 25x25x3mm 304 stainless angle:

**In Stock:**
- 12m available at $45.20/m (cost $32.80/m) - Location: SS Rack

**Supplier Pricing:**
- Stainless Supplies: 25m available at $28.50/m
- AllSteel: 50m+ available at $31.20/m
- Steel Solutions: Don't stock stainless angle

You'd need to order 38m more from suppliers. Stainless Supplies has the best price."

## Implementation:

### 1. API Endpoints (`apps/quoting/views.py`, `apps/quoting/urls.py`) ✅ COMPLETED
jlh0vGbiAcpP0w1zabvvbcVLdalN0ojKNAs_E05Xl7nVRrkEnDcFFARwIFIIKRKw

#### Stock Search API ✅ COMPLETED
`GET /api/mcp/search_stock/?description=25x25x3mm+angle&metal_type=steel&limit=20`

**Test Results:**
- ✅ API endpoint working: `http://localhost:8000/quoting/api/mcp/search_stock/`
- ✅ Authentication working: Requires X-API-Key header
- ✅ Returns proper JSON format with stock_items array

**Optional Parameters:**
- `metal_type=steel` - Filter by metal type
- `alloy=304` - Filter by alloy type
- `min_quantity=10` - Minimum quantity required
- `limit=20` - Maximum results (default 20)

**Response Format:**
```json
{
  "stock_items": [
    {
      "description": "25x25x3mm Steel Angle",
      "quantity": 45.0,
      "unit_cost": 8.30,
      "retail_price": 12.50,
      "location": "Rack A3",
      "metal_type": "steel",
      "alloy": null
    }
  ]
}
```

#### Supplier Prices Search API
`GET /api/mcp/search_supplier_prices/?description=25x25x3mm+angle&metal_type=steel&limit=20`

**Optional Parameters:**
- `suppliers=steel-solutions,metro-steel` - Filter by specific suppliers
- `include_internal_stock=true` - Include our stock as "Internal Stock" supplier
- `metal_type=steel` - Filter by metal type
- `alloy=304` - Filter by alloy type
- `limit=20` - Maximum results (default 20)

**Response Format:**
```json
{
  "supplier_prices": [
    {
      "product_name": "25x25x3mm Steel Angle 6m lengths",
      "supplier_name": "Steel Solutions",
      "price": 7.20,
      "available_stock": 50,
      "price_unit": "per metre",
      "metal_type": "steel",
      "item_no": "SA25x25x3"
    },
    {
      "product_name": "25x25x3mm Steel Angle",
      "supplier_name": "Internal Stock",
      "price": 12.50,
      "available_stock": 45,
      "price_unit": "per metre",
      "location": "Rack A3"
    }
  ]
}
```

#### Alternative Materials API
`GET /api/mcp/search_alternatives/?base_description=25x25x3mm+angle&metal_type=stainless&alloy=304`

#### Past Quotes Vector Search API
`POST /api/mcp/search_similar_quotes/`

**Request Body:**
```json
{
  "query": "warehouse steel angle framing",
  "limit": 5
}
```

**Response Format:**
```json
{
  "similar_quotes": [
    {
      "job_name": "Johnson Warehouse Extension",
      "client_name": "Johnson Construction",
      "quote_date": "2024-03-15",
      "materials_summary": "Steel angle framing, 60m @ $12.80/m",
      "total_value": 768.00,
      "similarity_score": 0.87,
      "context": "Warehouse structural framing using 25x25x3mm steel angle"
    }
  ]
}
```

#### Enriched Context API
`POST /api/mcp/get_enriched_context/`

**Request Body:**
```json
{
  "material_query": "steel angle warehouse",
  "include_trends": true,
  "include_recommendations": true
}
```

**Response Format:**
```json
{
  "material_insights": [
    "25x25x3mm Steel Angle commonly used for warehouse framing",
    "Typical warehouse jobs use 50-200m depending on span"
  ],
  "pricing_context": [
    "Recent jobs averaged $12.50/m for similar specifications",
    "Steel prices up 8% in last 6 months"
  ],
  "recommendations": [
    "Metro Steel typically best value for bulk orders",
    "Consider 12m lengths to minimize cuts and waste"
  ]
}
```

#### Job Context API (for "Interactive Quote" button) ✅ COMPLETED
`GET /api/mcp/job_context/{job_id}/`

**Test Results:**
- ✅ API endpoint working: `http://localhost:8000/quoting/api/mcp/job_context/{job_id}/`
- ✅ Authentication working: Requires X-API-Key header
- ✅ Returns job details, existing materials, and client history
- ✅ Error handling: Returns 404 for non-existent jobs

**Response Format:**
```json
{
  "job": {
    "id": "uuid",
    "name": "Johnson Warehouse Extension",
    "client_name": "Johnson Construction",
    "description": "Steel frame warehouse extension",
    "status": "quoting"
  },
  "existing_materials": [
    {
      "description": "Steel angle preliminary estimate",
      "quantity": 50.0,
      "notes": "For main frame"
    }
  ],
  "client_history": [
    "Previous jobs used Metro Steel supplier",
    "Typically prefers 12m lengths to minimize cuts"
  ]
}
```

### 2. Vector Embedding Implementation

#### Database Schema
Add to Django models:
```python
class QuoteEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    job = models.ForeignKey('job.Job', on_delete=models.CASCADE)
    content = models.TextField()  # Original quote description
    embedding = models.JSONField()  # Vector embedding array
    metadata = models.JSONField()  # Job type, materials, client, etc.
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Vector Search Service
- Use sentence-transformers or OpenAI embeddings API
- Store embeddings in PostgreSQL with pgvector or in separate vector DB
- Cosine similarity search for similar quotes

### 3. Quote Request Logging

#### Database Schema
```python
class QuoteSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    job = models.ForeignKey('job.Job', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    final_pricing = models.JSONField(blank=True, null=True)
    session_context = models.TextField()  # Full conversation context

class QuoteInteraction(models.Model):
    session = models.ForeignKey(QuoteSession, on_delete=models.CASCADE)
    user_input = models.TextField()
    system_response = models.TextField()
    mcp_calls = models.JSONField()  # Log of MCP API calls made
    timestamp = models.DateTimeField(auto_now_add=True)
```

#### Quote Session APIs
`POST /api/mcp/start_quote_session/` - Create new session for a job
`POST /api/mcp/log_interaction/` - Log each user/assistant exchange
`POST /api/mcp/finalize_quote/` - Save final pricing and generate embedding

### 4. Authentication ✅ COMPLETED
- ✅ ServiceAPIKey model created in `apps/workflow/models/service_api_key.py`
- ✅ Authentication middleware in `apps/workflow/authentication.py`
- ✅ Management command to create API keys: `python manage.py create_service_api_key`
- ✅ Test API key created: `jlh0vGbiAcpP0w1zabvvbcVLdalN0ojKNAs_E05Xl7nVRrkEnDcFFARwIFIIKRKw`

**Usage**: Include `X-API-Key: <service_key>` header in MCP API requests

### 5. Response Format
Return JSON combining Stock and SupplierProduct data:
- **Stock items**: description, quantity, unit_cost, retail_price, location, metal_type, alloy
- **Supplier products**: product_name, supplier_name, variant_price, variant_available_stock, price_unit, metal_type
