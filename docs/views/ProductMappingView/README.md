# Product Mapping Views Documentation

## Business Purpose
Provides product parsing mapping validation functionality for supplier pricing data in jobbing shop operations. Handles validation and correction of AI-parsed supplier product data, ensuring accurate material specifications and pricing. Essential for maintaining data quality in supplier price lists, enabling accurate quoting, and supporting procurement decision-making.

## Views

### product_mapping_validation
**File**: `apps/purchasing/views/product_mapping.py`
**Type**: Function-based view
**URL**: `/purchasing/product-mapping/`

#### What it does
- Provides interface for validating AI-parsed supplier product mappings
- Displays unvalidated mappings prioritized for review
- Shows validation statistics and progress tracking
- Enables quality control for automated product data parsing
- Supports manual correction and verification of AI parsing results

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Product mapping validation template with mappings and statistics
  - Unvalidated mappings prioritized first
  - Validated mappings for context and reference
  - Validation statistics and progress metrics

#### Integration
- ProductParsingMapping model for mapping data
- Xero status updates for mapping validation
- Template-based interface for validation workflow
- Statistics calculation for validation progress

### validate_mapping
**File**: `apps/purchasing/views/product_mapping.py`
**Type**: Function-based view (POST only)
**URL**: `/purchasing/api/product-mapping/<uuid:mapping_id>/validate/`

#### What it does
- Validates and updates specific product parsing mappings
- Handles manual corrections to AI-parsed product data
- Updates validation status with user and timestamp tracking
- Propagates validated data to related supplier products
- Manages Xero integration status for validated mappings

#### Parameters
- `mapping_id`: UUID of mapping to validate (path parameter)
- Form data with validation updates:
  - `mapped_item_code`: Corrected item code
  - `mapped_description`: Corrected product description
  - `mapped_metal_type`: Corrected material type
  - `mapped_alloy`: Corrected alloy specification
  - `mapped_specifics`: Corrected specific details
  - `mapped_dimensions`: Corrected dimensional data
  - `mapped_unit_cost`: Corrected unit pricing
  - `mapped_price_unit`: Corrected pricing unit
  - `validation_notes`: User notes about validation

#### Returns
- **200 OK**: JSON success response with update confirmation
  - `success`: True
  - `message`: Validation confirmation with update count
- **400 Bad Request**: Invalid unit cost format or validation errors
- **404 Not Found**: Mapping not found
- **500 Internal Server Error**: System failures during validation

#### Integration
- ProductParsingMapping model for validation updates
- SupplierProduct model for data propagation
- User tracking for validation accountability
- Xero status integration for accounting system sync

## Validation Features
- **AI Correction**: Manual correction of automated parsing results
- **Data Propagation**: Validated mappings update related supplier products
- **Progress Tracking**: Statistics on validation completion rates
- **Quality Control**: User validation with notes and timestamps
- **Xero Integration**: Mapping validation affects accounting system status

## Error Handling
- **400 Bad Request**: Invalid unit cost format or malformed data
- **404 Not Found**: Mapping not found for validation
- **500 Internal Server Error**: System failures or database errors
- Comprehensive logging for debugging and audit trails
- User-friendly error messages for validation workflow

## Business Rules
- Unvalidated mappings are prioritized for review
- User validation creates audit trail with timestamps
- Validated data propagates to all related supplier products
- Mapping validation affects Xero integration status
- Unit cost validation ensures proper decimal formatting
- Validation notes support quality control documentation

## Integration Points
- **ProductParsingMapping Model**: Core mapping data for validation
- **SupplierProduct Model**: Related products for data propagation
- **User Model**: Validation accountability and tracking
- **Xero Integration**: Status updates for accounting system
- **AI Parsing System**: Correction of automated parsing results

## Data Quality Management
- **Manual Review**: Human validation of AI parsing results
- **Correction Workflow**: Interface for data quality improvements
- **Propagation Logic**: Validated data updates related records
- **Statistics Tracking**: Progress monitoring for validation completion
- **Audit Trail**: Complete validation history with user tracking

## Performance Considerations
- Efficient mapping ordering with database optimization
- Bulk updates for related supplier products
- Optimized statistics calculation for progress tracking
- Xero status updates with caching consideration
- Minimal database queries for validation operations

## Security Considerations
- User authentication for validation operations
- Input validation for all mapping fields
- Error message sanitization to prevent information leakage
- Audit logging for validation tracking and compliance
- Proper handling of sensitive pricing data

## AI Integration Support
- **Parsing Correction**: Manual fixes for AI automation results
- **Quality Feedback**: Validation creates training data for AI improvement
- **Automation Balance**: Human oversight for AI-processed data
- **Accuracy Improvement**: Iterative refinement of parsing quality
- **Data Confidence**: Validation increases data reliability

## Workflow Integration
- **Supplier Management**: Product data quality for procurement
- **Quoting System**: Accurate pricing data for estimate generation
- **Inventory Management**: Correct material specifications
- **Accounting Integration**: Validated data for financial systems
- **Quality Control**: Systematic review of automated processes

## Related Views
- Quoting views for price list utilization
- Supplier product views for pricing management
- Purchase order views for procurement workflow
- Xero views for accounting integration
- AI processing views for automation management