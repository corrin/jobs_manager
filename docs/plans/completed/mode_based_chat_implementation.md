# Mode-Based Quote Chat Implementation Plan

## Executive Summary

Replace the current monolithic Gemini chat service with a mode-based system providing three focused tools (CALC, PRICE, TABLE) for accelerating quoting workflows. This solves the problem of premature tool usage while maintaining simplicity and user control.

## Problem Statement

The current Gemini chat service immediately attempts pricing lookups for ambiguous requests instead of asking clarifying questions. This leads to:

- Incorrect quotes based on assumptions
- Wasted API calls to pricing services
- Poor user experience requiring constant corrections
- No structured data collection

## Solution: Mode-Based Architecture

### Core Concept

Instead of a complex state machine, implement three independent modes that the user can invoke as needed:

1. **CALC Mode** - Perform dimensions/areas/yield calculations
2. **PRICE Mode** - Map specifications to supplier SKUs and fetch prices
3. **TABLE Mode** - Format final quote with line items and totals

### Key Principles

- **Mode Isolation**: Each mode has exclusive access to specific tools
- **Structured Output**: JSON schemas enforce data structure
- **User Control**: Estimator decides workflow, not the system
- **Fail Fast**: Invalid inputs rejected immediately with clear questions
- **No Hidden State**: Each invocation is independent

## Detailed Design

### 1. System Architecture

```
User Input → Mode Detection → Mode Controller → Gemini API → JSON Response
                                 ↓
                           Tool Gating
                                 ↓
                           Schema Validation
```

### 2. Mode Specifications

#### CALC Mode

**Purpose**: Deterministic arithmetic for material calculations
**Tools**: None (pure computation)
**Input**: Part dimensions, quantities, sheet sizes, kerf
**Output**: Areas, yields, sheet counts, offcuts

#### PRICE Mode

**Purpose**: Match specifications to supplier products
**Tools**: `search_products`, `get_pricing_for_material`, `compare_suppliers`
**Input**: Normalized material spec, quantity
**Output**: Top 3 SKUs with pricing, lead times, delivery

#### TABLE Mode

**Purpose**: Generate final formatted quote
**Tools**: None (formatting only)
**Input**: Line items with costs, markup percentage
**Output**: Markdown table, subtotals, grand total

### 3. JSON Schemas

#### CALC Schema

```json
{
  "type": "object",
  "required": ["inputs", "results", "questions"],
  "properties": {
    "inputs": {
      "type": "object",
      "required": ["units"],
      "properties": {
        "units": { "type": "string", "enum": ["mm", "m"] },
        "part_dims_mm": {
          "type": "object",
          "properties": {
            "L": { "type": "number" },
            "W": { "type": "number" },
            "T": { "type": "number" }
          }
        },
        "qty": { "type": "integer", "minimum": 1 },
        "sheet_size_mm": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 2,
          "maxItems": 2
        },
        "kerf_mm": { "type": "number" }
      }
    },
    "results": {
      "type": "object",
      "properties": {
        "part_area_m2": { "type": "number" },
        "total_area_m2": { "type": "number" },
        "nest_yield_pct": { "type": "number" },
        "sheets_required": { "type": "integer" },
        "offcut_area_m2": { "type": "number" }
      }
    },
    "questions": {
      "type": "array",
      "items": { "type": "string" },
      "maxItems": 3
    }
  }
}
```

#### PRICE Schema

```json
{
  "type": "object",
  "required": ["normalized", "candidates", "questions"],
  "properties": {
    "normalized": {
      "type": "object",
      "required": ["family", "grade", "thickness_mm", "form"],
      "properties": {
        "family": { "type": "string" },
        "grade": { "type": "string" },
        "thickness_mm": { "type": "number" },
        "form": {
          "type": "string",
          "enum": ["sheet", "plate", "tube", "angle", "bar"]
        },
        "sheet_size_mm": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 2,
          "maxItems": 2
        },
        "qty_uom": { "type": "string", "enum": ["sheet", "kg", "m", "each"] },
        "qty_required": { "type": "number" }
      }
    },
    "candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["supplier", "sku", "uom", "price_per_uom"],
        "properties": {
          "supplier": { "type": "string" },
          "sku": { "type": "string" },
          "uom": { "type": "string" },
          "price_per_uom": { "type": "number" },
          "lead_time_days": { "type": "integer" },
          "delivery": { "type": "number" },
          "notes": { "type": "string" }
        }
      }
    },
    "questions": {
      "type": "array",
      "items": { "type": "string" },
      "maxItems": 3
    }
  }
}
```

#### TABLE Schema

```json
{
  "type": "object",
  "required": ["rows", "totals", "markdown", "questions"],
  "properties": {
    "rows": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["item", "qty", "uom", "unit_cost", "subtotal"],
        "properties": {
          "item": { "type": "string" },
          "qty": { "type": "number" },
          "uom": { "type": "string" },
          "unit_cost": { "type": "number" },
          "subtotal": { "type": "number" },
          "notes": { "type": "string" }
        }
      }
    },
    "totals": {
      "type": "object",
      "required": [
        "material",
        "labour",
        "freight",
        "overheads",
        "markup_pct",
        "grand_total_ex_gst"
      ],
      "properties": {
        "material": { "type": "number" },
        "labour": { "type": "number" },
        "freight": { "type": "number" },
        "overheads": { "type": "number" },
        "markup_pct": { "type": "number" },
        "grand_total_ex_gst": { "type": "number" }
      }
    },
    "markdown": { "type": "string" },
    "questions": {
      "type": "array",
      "items": { "type": "string" },
      "maxItems": 1
    }
  }
}
```

### 4. Prompt Templates

#### Global System Prompt (Minimal)

```
You are a quoting helper. Do one job at a time in the requested MODE.
- MODE=CALC: perform deterministic arithmetic from given specs. No prices.
- MODE=PRICE: map normalized spec to supplier SKUs; call pricing tools only.
- MODE=TABLE: output a final table from given line items; no new math or prices.

Always return strict JSON that matches the provided SCHEMA. No prose.
If input is ambiguous, ask ≤3 precise questions in the JSON and stop.
Never invent missing numeric values. Never call tools in the wrong mode.
```

#### Mode-Specific Prompt Templates

**CALC Prompt**

```
MODE=CALC
SCHEMA: {calc_schema}
INPUT: {user_input}
TASK: Compute area, yield, sheets_required. If anything essential is missing, ask ≤3 questions and stop.
```

**PRICE Prompt**

```
MODE=PRICE
SCHEMA: {price_schema}
INPUT: {normalized_spec}
TASK: Map to SKUs and return top 3 with price_per_uom, lead_time_days, delivery.
Do not ask for dimensions; only grade/form/size/qty if missing.
```

**TABLE Prompt**

```
MODE=TABLE
SCHEMA: {table_schema}
INPUT: {line_items}
TASK: Calculate subtotals, totals, and emit a neat Markdown table.
```

### 5. Controller Implementation

```python
class QuoteModeController:
    """Controls mode-based quote generation."""

    MODES = ["CALC", "PRICE", "TABLE"]

    def __init__(self):
        self.schemas = {
            "CALC": load_calc_schema(),
            "PRICE": load_price_schema(),
            "TABLE": load_table_schema()
        }
        self.tools = {
            "CALC": [],
            "PRICE": ["search_products", "get_pricing_for_material", "compare_suppliers"],
            "TABLE": []
        }

    def run(self, mode: str, user_input: str, job_ctx: dict) -> tuple[dict, bool]:
        """
        Execute a mode with the given input.

        Returns:
            tuple: (response_data, has_questions)
        """
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode: {mode}")

        schema = self.schemas[mode]
        allowed_tools = self.tools[mode]
        prompt = self.render_prompt(mode, user_input, job_ctx, schema)

        # Call Gemini with mode-specific configuration
        response = self.call_gemini(prompt, allowed_tools, schema)

        # Validate response against schema
        validated_data = self.validate_json(response, schema)

        # Check if there are questions
        questions = validated_data.get("questions", [])
        has_questions = len(questions) > 0

        return validated_data, has_questions

    def infer_mode(self, user_input: str) -> str:
        """Detect mode from user input patterns."""
        input_lower = user_input.lower()

        # CALC indicators
        if any(word in input_lower for word in ["area", "yield", "sheets", "nest", "dimensions", "qty"]):
            return "CALC"

        # PRICE indicators
        if any(word in input_lower for word in ["price", "cost", "supplier", "quote", "sku"]):
            return "PRICE"

        # TABLE indicators
        if any(word in input_lower for word in ["table", "summary", "total", "final"]):
            return "TABLE"

        # Default to CALC for ambiguous input
        return "CALC"
```

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1)

1. Create `apps/job/schemas/quote_mode_schemas.py`
2. Create `apps/job/services/quote_mode_controller.py`
3. Add schema validation utilities

### Phase 2: Service Integration (Day 2)

1. Update `apps/job/services/gemini_chat_service.py`:
   - Add mode parameter to `generate_ai_response()`
   - Implement mode-specific tool filtering
   - Replace complex system prompt with minimal version
2. Create `apps/job/services/mode_inference.py`

### Phase 3: API Updates (Day 3)

1. Update `apps/job/views/job_quote_chat_api.py`:
   - Add optional `mode` parameter
   - Store mode in metadata
   - Return mode hints
2. Add mode switching endpoints

### Phase 4: Testing (Day 4)

1. Create `apps/job/tests/test_quote_modes.py`
2. Test each mode with valid/invalid inputs
3. Test mode inference accuracy
4. Test tool gating enforcement

### Phase 5: UI Integration (Day 5)

1. Add mode selector buttons to chat interface
2. Display current mode indicator
3. Show mode-specific hints/examples
4. Auto-detect mode from input

## Edge Cases and Solutions

### Labour-Only Jobs

- Skip CALC mode entirely
- Use TABLE mode directly with labour line items
- No material calculations needed

### Stock Materials

- PRICE mode returns stock items with `supplier: "STOCK"`
- Zero lead time and delivery cost
- Include location/bin information in notes

### Mixed Scenarios

- PRICE mode handles both stock and external suppliers
- Returns mixed candidate list
- User selects appropriate items

### Simple Jobs

- User can jump directly to TABLE mode
- No enforcement of workflow sequence
- Maximum flexibility for experts

## Success Metrics

1. **Reduced API Calls**: 50% fewer unnecessary pricing lookups
2. **Faster Quotes**: Average quote time reduced by 30%
3. **Higher Accuracy**: 90% reduction in assumption-based errors
4. **User Satisfaction**: Positive feedback on control and flexibility

## Migration Strategy

### Week 1: Development

- Implement core system
- Internal testing

### Week 2: Beta Testing

- Deploy to 5 power users
- Gather feedback
- Refine mode inference

### Week 3: Gradual Rollout

- Feature flag for 25% of users
- Monitor metrics
- Fix edge cases

### Week 4: Full Deployment

- Enable for all users
- Deprecate old system
- Documentation and training

## Risks and Mitigations

| Risk                      | Impact | Mitigation                   |
| ------------------------- | ------ | ---------------------------- |
| Users confused by modes   | Medium | Clear UI with examples       |
| Mode inference errors     | Low    | Allow manual override        |
| Missing workflow guidance | Low    | Add optional AUTO mode later |
| Integration complexity    | Medium | Feature flag for rollback    |

## Future Enhancements

1. **AUTO Mode**: Chain modes intelligently based on input
2. **Mode Presets**: Save common mode sequences
3. **Batch Processing**: Run multiple calculations at once
4. **API Access**: Expose modes as REST endpoints
5. **Mobile Optimization**: Quick mode buttons for mobile UI

## Conclusion

The mode-based approach solves the immediate problem of premature tool usage while providing a simpler, more flexible system that respects user expertise. With clear schemas, enforced tool gating, and structured outputs, this design delivers predictable, accurate quotes without the complexity of a full state machine.
