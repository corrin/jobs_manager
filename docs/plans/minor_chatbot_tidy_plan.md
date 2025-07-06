# Minor Chatbot Tidy Plan

## Overview
This plan addresses minor coding standard issues identified in the chatbot implementation commits. The implementation is well-structured but needs refinement to meet project standards.

## Issues Identified

### 0. Hardcoded Model Names

As always, do not use fallbacks ever.  If something you need is unavailable (e.g. AI Provider model) then log the error and return

### 1. Hardcoded Model Names
**Priority: High**

Multiple services contain hardcoded AI model names that should be extracted to configuration:

#### MCP Chat Service (`apps/job/services/mcp_chat_service.py`)
- **Lines 258, 355, 372**: `"claude-3-5-sonnet-20241022"` hardcoded
- **Fix**: Use `ai_provider.model_name`

#### Gemini Chat Service (`apps/job/services/gemini_chat_service.py`)
- **Line 66**: `"gemini-2.5-flash-lite-preview-06-17"` hardcoded fallback
- **Fix**: Use `ai_provider.model_name` and fail if not configured

#### Other Services
- **Product Parser** (`apps/quoting/services/product_parser.py:47`): Has TODO comment already
- **Quote to PO Service** (`apps/purchasing/services/quote_to_po_service.py:267,611`): Multiple hardcoded models
- **Claude Price List Extraction** (`apps/quoting/services/claude_price_list_extraction.py:159`)

### 2. Configuration Usage Improvement
**Priority: High**

The `AIProvider` model already has a `model_name` field that should be used consistently. Services should use this field instead of hardcoded fallbacks and fail properly if not configured.

### 3. API Provider Query Optimization
**Priority: Medium**

Current pattern queries default providers each time:
```python
ai_provider = AIProvider.objects.filter(
    provider_type=AIProviderTypes.GOOGLE,
    default=True,
).first()
```

**Recommendations:**
- Consider caching default providers
- Add `select_related('company')` if needed
- Query patterns are acceptable for current usage

### 4. Missing Job Foreign Key Assignments
**Priority: High - RESOLVED**

**Status**: ✅ **No Issues Found**

All `JobQuoteChat.objects.create()` calls properly include `job=job` parameter:
- **Gemini Chat Service**: Lines 254 and 269 both include job assignment
- **MCP Chat Service**: Lines 248 include job assignment

## Implementation Steps

### Step 1: Use AIProvider.model_name Consistently
1. Remove all hardcoded model names from services
2. Update all services to use `ai_provider.model_name` directly
3. Use the error persistence pattern for configuration errors:
   ```python
   if not ai_provider.model_name:
       from apps.workflow.services.error_persistence import persist_app_error
       error = ValueError("AI provider model_name is required")
       persist_app_error(error)
       return JobQuoteChat.objects.create(
           job=job,
           message_id=f"assistant-error-{uuid.uuid4()}",
           role="assistant",
           content="Configuration error: AI provider model not configured",
           metadata={"error": True, "error_type": "configuration"}
       )
   ```

### Step 2: Update Service Classes
1. **MCP Chat Service** - Replace 3 hardcoded instances
2. **Gemini Chat Service** - Replace 1 hardcoded instance
3. **Other Services** - Address remaining hardcoded models

### Step 3: Code Quality Improvements
1. Ensure consistent error handling patterns
2. Verify all services use the AIProvider model consistently
3. Add model name validation if needed
4. Run the linter, type checker, etc.

## Files to Modify

### High Priority
- `apps/job/services/mcp_chat_service.py` (3 instances)
- `apps/job/services/gemini_chat_service.py` (1 instance)

### Medium Priority
- `apps/purchasing/services/quote_to_po_service.py` (2 instances)
- `apps/quoting/services/claude_price_list_extraction.py` (1 instance)
- `apps/quoting/services/product_parser.py` (1 instance - already has TODO)

## Risk Assessment

**Risk Level: Low**
- Changes are configuration-related, not logic changes
- Existing functionality remains unchanged
- AI provider infrastructure already exists
- No breaking changes to API endpoints

## Testing Requirements

1. **Unit Tests**: Verify model name resolution logic
2. **Integration Tests**: Ensure chat services work with configuration
3. **Manual Testing**: Test default provider scenarios

## Expected Outcomes

1. **Maintainability**: Centralized model configuration
2. **Flexibility**: Easy model updates without code changes
3. **Consistency**: Uniform approach across all AI services
4. **Compliance**: Meets project coding standards

## Approval Status

✅ **APPROVED WITH MINOR CHANGES**

The chatbot implementation is solid and production-ready. These changes address code quality standards while maintaining the excellent architecture and functionality already implemented.
