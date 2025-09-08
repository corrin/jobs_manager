Got it — keep it lean and useful. Here’s a minimal, user-driven design that accelerates arithmetic, price lookups, and table generation without ceremony.

Core idea

One assistant, three modes:

CALC → do dimensions/areas/yield math.

PRICE → map spec to SKUs and fetch prices.

TABLE → format the final line items.

The user triggers the mode (or you infer from intent). No multi-step FSM, no sign-off gates. Each mode has a tiny JSON schema so your controller can trust outputs and wire tools.

1) Single, small system prompt
You are a quoting helper. Do one job at a time in the requested MODE.
- MODE=CALC: perform deterministic arithmetic from given specs. No prices.
- MODE=PRICE: map normalized spec to supplier SKUs; call pricing tools only.
- MODE=TABLE: output a final table from given line items; no new math or prices.

Always return strict JSON that matches the provided SCHEMA. No prose.
If input is ambiguous, ask ≤3 precise questions in the JSON and stop.
Never invent missing numeric values. Never call tools in the wrong mode.

2) Tiny schemas (copy/paste)
CALC (areas, cuts, yields, sheet counts)
{
  "type": "object",
  "required": ["inputs", "results", "questions"],
  "properties": {
    "inputs": {
      "type": "object",
      "required": ["units"],
      "properties": {
        "units": {"type":"string","enum":["mm","m"]},
        "part_dims_mm": {"type":"object","properties":{"L":{"type":"number"},"W":{"type":"number"},"T":{"type":"number"}}},
        "qty": {"type":"integer","minimum":1},
        "sheet_size_mm": {"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2},
        "kerf_mm": {"type":"number"}
      }
    },
    "results": {
      "type":"object",
      "properties": {
        "part_area_m2": {"type":"number"},
        "total_area_m2": {"type":"number"},
        "nest_yield_pct": {"type":"number"},
        "sheets_required": {"type":"integer"},
        "offcut_area_m2": {"type":"number"}
      }
    },
    "questions": {"type":"array","items":{"type":"string"}, "maxItems": 3}
  }
}

PRICE (map to SKU + prices)
{
  "type":"object",
  "required":["normalized","candidates","questions"],
  "properties":{
    "normalized":{
      "type":"object",
      "required":["family","grade","thickness_mm","form"],
      "properties":{
        "family":{"type":"string"}, "grade":{"type":"string"},
        "thickness_mm":{"type":"number"},
        "form":{"type":"string","enum":["sheet","plate","tube","angle","bar"]},
        "sheet_size_mm":{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2},
        "qty_uom":{"type":"string","enum":["sheet","kg","m","each"]},
        "qty_required":{"type":"number"}
      }
    },
    "candidates":{
      "type":"array",
      "items":{
        "type":"object",
        "required":["supplier","sku","uom","price_per_uom"],
        "properties":{
          "supplier":{"type":"string"},
          "sku":{"type":"string"},
          "uom":{"type":"string"},
          "price_per_uom":{"type":"number"},
          "lead_time_days":{"type":"integer"},
          "delivery":{"type":"number"},
          "notes":{"type":"string"}
        }
      }
    },
    "questions":{"type":"array","items":{"type":"string"}, "maxItems": 3}
  }
}

TABLE (final presentation)
{
  "type":"object",
  "required":["rows","totals","markdown","questions"],
  "properties":{
    "rows":{
      "type":"array",
      "items":{
        "type":"object",
        "required":["item","qty","uom","unit_cost","subtotal"],
        "properties":{
          "item":{"type":"string"},
          "qty":{"type":"number"},
          "uom":{"type":"string"},
          "unit_cost":{"type":"number"},
          "subtotal":{"type":"number"},
          "notes":{"type":"string"}
        }
      }
    },
    "totals":{
      "type":"object",
      "required":["material","labour","freight","overheads","markup_pct","grand_total_ex_gst"],
      "properties":{
        "material":{"type":"number"},
        "labour":{"type":"number"},
        "freight":{"type":"number"},
        "overheads":{"type":"number"},
        "markup_pct":{"type":"number"},
        "grand_total_ex_gst":{"type":"number"}
      }
    },
    "markdown":{"type":"string"},
    "questions":{"type":"array","items":{"type":"string"}, "maxItems": 1}
  }
}

3) Controller (≈40 lines)
def run(mode, user_input, job_ctx):
    schema = load_schema(mode)
    tools = {"CALC": [], "PRICE": ["catalog.search","pricing.lookup"], "TABLE": []}[mode]
    prompt = render(mode, user_input, job_ctx, schema)
    out = llm(prompt, tools=tools, response_format="json_object")
    data = json_validate(out, schema)
    q = data.get("questions", [])
    return data, (len(q) > 0)


You keep transitions manual: the user (or UI buttons) says “Next: PRICE” or “Next: TABLE”. That’s it.

4) Fast UX patterns (what the estimator sees)

CALC: “Parts: 100×100×0.9 mm, qty 12; sheets 1220×2440; kerf 0.2” → returns area, yield, sheets required.
If thickness missing, it asks once.

PRICE: Takes normalized spec and qty; returns 3 SKUs with price/lead/delivery.
If grade ambiguous, asks “304 or 316?” and stops.

TABLE: Takes chosen SKUs + labour minutes × rates → returns ready-to-paste Markdown table + totals.

5) Guardrails (minimal, practical)

No tool use in CALC/TABLE. Enforced by mode → tools map.

≤3 questions rule. Forces crisp clarifications, no rambling.

Never invent numbers. If a number is required and missing, ask.

Units normalization in CALC only. Keep conversions in one place.

6) Example prompts (concise)
CALC prompt
MODE=CALC
SCHEMA: <CALC JSON schema>
INPUT:
- units:mm
- part_dims_mm: L=300, W=180, T=0.9
- qty: 20
- sheet_size_mm: [1220,2440]
- kerf_mm: 0.2
TASK: Compute area, yield, sheets_required. If anything essential is missing, ask ≤3 questions and stop.

PRICE prompt
MODE=PRICE
SCHEMA: <PRICE JSON schema>
INPUT (normalized from CALC/user):
family: stainless, grade: 304, thickness_mm: 0.9, form: sheet,
sheet_size_mm: [1220,2440], qty_uom: sheet, qty_required: 3
TASK: Map to SKUs and return top 3 with price_per_uom, lead_time_days, delivery.
Do not ask for dimensions; only grade/form/size/qty if missing.

TABLE prompt
MODE=TABLE
SCHEMA: <TABLE JSON schema>
INPUT:
rows:
- item: "SS304 0.9mm 1220x2440 (XYZ SS304-0.9-1220x2440)", qty:3, uom:"sheet", unit_cost:189.00
- item: "Laser + Bend labour", qty:1, uom:"lot", unit_cost:235.40
- item: "Delivery", qty:1, uom:"each", unit_cost:25.00
totals_hint: markup_pct=15, freight_in_rows=true
TASK: Calculate subtotals, totals, and emit a neat Markdown table.

7) Why this meets your goal

Arithmetic speed: CALC is deterministic and instant.

Price speed: PRICE only needs a normalized spec; returns 2–3 candidates.

Mechanical table: TABLE composes numbers you already have; no new logic.

No overcooked FSM. No hidden transitions. Estimator stays in control, one clear step at a time.

If you want, I can draft the three render(mode, …) prompt templates exactly as Python f-strings and a couple of pytest golden tests (CALC happy-path + PRICE missing-grade).
