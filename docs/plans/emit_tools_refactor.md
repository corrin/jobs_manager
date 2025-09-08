# Emit Tools Refactor Plan

## Problem Statement
Gemini API has a limitation: it cannot use function calling (tools) and enforce JSON response format (`response_mime_type="application/json"`) simultaneously. This causes PRICE mode to fail since it needs both tools (to search products) and structured JSON output.

## Solution: Emit Tools Pattern
Instead of forcing JSON response format, we'll use dedicated "emit" tools that accept structured data as their parameters. The model will call these tools with the final results, giving us validated JSON through tool arguments.

## Implementation Steps

### 1. Define Emit Tools for Each Mode

#### Location: `/apps/job/services/quote_mode_controller.py`

Add three new tool definitions in `get_mcp_tools_for_mode()`:

```python
"emit_calc_result": FunctionDeclaration(
    name="emit_calc_result",
    description="Emit the final calculation results in structured format",
    parameters={
        "type": "object",
        "required": ["inputs", "results", "questions"],
        "properties": {
            "inputs": {
                "type": "object",
                "properties": {
                    "raw_input": {"type": "string"},
                    "parsed": {"type": "object"}
                }
            },
            "results": {
                "type": "object",
                "required": ["items", "assumptions"],
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["description", "quantity", "unit"],
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                                "specs": {"type": "object"}
                            }
                        }
                    },
                    "assumptions": {"type": "string"}
                }
            },
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3
            }
        }
    }
),

"emit_price_result": FunctionDeclaration(
    name="emit_price_result",
    description="Emit the final pricing results in structured format",
    parameters={
        "type": "object",
        "required": ["normalized", "candidates", "questions"],
        "properties": {
            "normalized": {
                "type": "object",
                "required": ["family", "grade", "thickness_mm", "form"],
                "properties": {
                    "family": {"type": "string"},
                    "grade": {"type": "string"},
                    "thickness_mm": {"type": "number"},
                    "form": {"type": "string", "enum": ["sheet", "plate", "tube", "angle", "bar"]},
                    "sheet_size_mm": {"type": "array", "items": {"type": "number"}},
                    "qty_uom": {"type": "string", "enum": ["sheet", "kg", "m", "each"]},
                    "qty_required": {"type": "number"}
                }
            },
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["supplier", "sku", "uom", "price_per_uom"],
                    "properties": {
                        "supplier": {"type": "string"},
                        "sku": {"type": "string"},
                        "uom": {"type": "string"},
                        "price_per_uom": {"type": "number"},
                        "lead_time_days": {"type": "integer"},
                        "delivery": {"type": "number"},
                        "notes": {"type": "string"}
                    }
                }
            },
            "questions": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
        }
    }
),

"emit_table_result": FunctionDeclaration(
    name="emit_table_result",
    description="Emit the final table results in structured format",
    parameters={
        "type": "object",
        "required": ["rows", "totals", "markdown", "questions"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["item", "qty", "uom", "unit_cost", "subtotal"],
                    "properties": {
                        "item": {"type": "string"},
                        "qty": {"type": "number"},
                        "uom": {"type": "string"},
                        "unit_cost": {"type": "number"},
                        "subtotal": {"type": "number"},
                        "notes": {"type": "string"}
                    }
                }
            },
            "totals": {
                "type": "object",
                "required": ["material", "labour", "freight", "overheads", "markup_pct", "grand_total_ex_gst"],
                "properties": {
                    "material": {"type": "number"},
                    "labour": {"type": "number"},
                    "freight": {"type": "number"},
                    "overheads": {"type": "number"},
                    "markup_pct": {"type": "number"},
                    "grand_total_ex_gst": {"type": "number"}
                }
            },
            "markdown": {"type": "string"},
            "questions": {"type": "array", "items": {"type": "string"}, "maxItems": 1}
        }
    }
)
```

### 2. Update Tool Mappings

#### Location: `/apps/job/schemas/quote_mode_schemas.py`

Update `get_allowed_tools()`:

```python
def get_allowed_tools(mode: str) -> list:
    tools = {
        "CALC": ["emit_calc_result"],  # Only emit tool
        "PRICE": ["search_products", "get_pricing_for_material", "compare_suppliers", "emit_price_result"],  # Search + emit
        "TABLE": ["emit_table_result"],  # Only emit tool
    }
    # ...
```

### 3. Modify Response Processing

#### Location: `/apps/job/services/quote_mode_controller.py` - `run()` method

Replace current response processing with:

```python
def run(self, mode, user_input, job=None, gemini_client=None, chat_history=None):
    # ... existing setup code ...

    # Remove JSON format enforcement
    generation_config = None  # Let Gemini respond naturally

    # Start chat with history
    if chat_history:
        chat = gemini_client.start_chat(history=chat_history)
    else:
        chat = gemini_client.start_chat()

    # Send message with tools
    response = chat.send_message(prompt, tools=allowed_tools)

    # Process response to find emit tool call
    emit_tool_name = f"emit_{mode.lower()}_result"
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        # Check if response contains our emit tool call
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                if part.function_call.name == emit_tool_name:
                    # Extract and validate the result
                    result_data = dict(part.function_call.args)
                    validated_data = self.validate_json(result_data, schema)

                    # Check for questions
                    questions = validated_data.get("questions", [])
                    has_questions = len(questions) > 0

                    return validated_data, has_questions
                else:
                    # Handle other tool calls (for PRICE mode)
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args)

                    # Execute the tool (need to add tool execution logic)
                    tool_result = self._execute_tool(tool_name, tool_args)

                    # Send tool result back to continue conversation
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=tool_name,
                                    response={"result": tool_result}
                                )
                            )]
                        )
                    )

        # If no tool calls in response, prompt for emit tool
        if iteration == 0:
            response = chat.send_message(
                f"Please call the {emit_tool_name} tool with your final results."
            )

        iteration += 1

    # If we get here, something went wrong
    raise ValueError(f"Model did not call {emit_tool_name} after {max_iterations} attempts")
```

### 4. Add Tool Execution Logic

#### Location: `/apps/job/services/quote_mode_controller.py`

Add method to execute MCP tools:

```python
def _execute_tool(self, tool_name: str, arguments: dict) -> str:
    """Execute a tool and return its result."""
    # Import the quoting tools
    from apps.quoting.mcp import QuotingTool

    quoting_tool = QuotingTool()
    tool_map = {
        "search_products": quoting_tool.search_products,
        "get_pricing_for_material": quoting_tool.get_pricing_for_material,
        "compare_suppliers": quoting_tool.compare_suppliers,
    }

    if tool_name in tool_map:
        return tool_map[tool_name](**arguments)
    elif tool_name.startswith("emit_"):
        # Emit tools don't need execution, they're terminal
        return None
    else:
        return f"Unknown tool: {tool_name}"
```

### 5. Update System and Mode Prompts

#### Location: `/apps/job/services/quote_mode_controller.py`

Update `get_system_prompt()`:

```python
def get_system_prompt(self) -> str:
    return """You are a quoting helper. Process requests in the specified MODE.
- MODE=CALC: Calculate quantities and dimensions. Call emit_calc_result with your final results.
- MODE=PRICE: Search for materials and pricing. Call emit_price_result with your final results.
- MODE=TABLE: Format quote tables. Call emit_table_result with your final results.

IMPORTANT: You MUST call the appropriate emit_[mode]_result tool to submit your final answer.
The emit tool call should contain all required fields according to the schema.
Make reasonable assumptions and state them. Avoid asking questions unless truly blocked."""
```

Update mode task descriptions:

```python
mode_tasks = {
    "CALC": "Calculate required items from specifications. Call emit_calc_result with the complete results.",
    "PRICE": "Search for materials and pricing using the available tools, then call emit_price_result with all findings.",
    "TABLE": "Format the quote data into a table and call emit_table_result with the formatted output.",
}
```

## Testing Strategy

1. **CALC Mode Test**
   - Input: "3 stainless steel boxes, 700×700×400mm, 0.8mm thick, open top"
   - Expected: Model calls `emit_calc_result` with calculated flat patterns and assumptions

2. **PRICE Mode Test**
   - Input: "Price the materials from the previous calculation"
   - Expected: Model calls search tools, then `emit_price_result` with candidates

3. **TABLE Mode Test**
   - Input: "Create a quote table with the pricing"
   - Expected: Model calls `emit_table_result` with formatted table

## Benefits

1. **Resolves Gemini Limitation**: No conflict between tools and JSON format
2. **Single-Pass Operation**: One conversation turn gets complete results
3. **Validated Output**: Tool parameters are already JSON and validated by Gemini
4. **Clear Terminal Action**: Each mode has a defined endpoint
5. **Maintains Tool Usage**: PRICE mode can still search and gather data

## Risks and Mitigations

1. **Risk**: Model might not call emit tool
   - **Mitigation**: Prompt engineering + retry logic with explicit instructions

2. **Risk**: Tool execution failures in PRICE mode
   - **Mitigation**: Error handling with graceful fallbacks

3. **Risk**: Schema mismatch between emit tool and validation
   - **Mitigation**: Single source of truth for schemas

## Rollback Plan

If this approach fails:
1. Revert to original code (git history)
2. Consider two-pass approach: gather data with tools, then format without tools
3. Or server-side assembly: let model be a planner only, server builds the JSON
