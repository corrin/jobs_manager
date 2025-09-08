"""
Quote Mode Controller

Manages mode-based quote generation with structured JSON schemas and tool gating.
Provides CALC, PRICE, and TABLE modes for focused quoting operations.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from google.generativeai.types import FunctionDeclaration

from apps.job.models import Job
from apps.job.schemas import quote_mode_schemas

logger = logging.getLogger(__name__)


class QuoteModeController:
    """
    Controls mode-based quote generation with strict schema validation
    and tool gating to prevent premature operations.
    """

    MODES = ["CALC", "PRICE", "TABLE"]

    def __init__(self):
        """Initialize the controller with schemas and tool mappings."""
        self.schemas = {
            mode: quote_mode_schemas.get_schema(mode) for mode in self.MODES
        }
        self.tools = {
            mode: quote_mode_schemas.get_allowed_tools(mode) for mode in self.MODES
        }

    def get_system_prompt(self) -> str:
        """
        Get the minimal system prompt for mode-based operation.

        Returns:
            The system prompt string
        """
        return """You are a quoting helper. Do one job at a time in the requested MODE.
- MODE=CALC: Calculate quantities and dimensions from specifications. Output a list of items with quantities and units. No prices.
- MODE=PRICE: map normalized spec to supplier SKUs; call pricing tools only.
- MODE=TABLE: output a final table from given line items; no new math or prices.

Always return strict JSON that matches the provided SCHEMA. ALL fields marked as "required" in the schema MUST have valid values, never null or missing.
ALWAYS make reasonable assumptions and explicitly state them in the 'assumptions' field. Avoid asking questions - just pick sensible defaults (e.g., 3mm thickness for sheet metal, 304 for stainless steel, open-top for boxes).
Never call tools in the wrong mode."""

    def render_prompt(
        self,
        mode: str,
        user_input: str,
        job_ctx: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render a mode-specific prompt.

        Args:
            mode: The operation mode (CALC, PRICE, or TABLE)
            user_input: User's input text
            job_ctx: Optional job context information
            schema: Optional schema override

        Returns:
            The formatted prompt string
        """
        if schema is None:
            schema = self.schemas[mode]

        job_info = ""
        if job_ctx:
            job_info = f"\nJOB_CONTEXT: Job #{job_ctx.get('job_number', 'N/A')} for {job_ctx.get('client', 'N/A')}"

        mode_tasks = {
            "CALC": "Calculate required items from specifications. Output a list of what's needed with quantities and units.",
            "PRICE": "Use pricing tools to search supplier database. Return the actual results from the tools.",
            "TABLE": "Calculate subtotals, totals, and emit a neat Markdown table.",
        }

        return f"""MODE={mode}
SCHEMA: {json.dumps(schema, indent=2)}{job_info}
CURRENT INPUT: {user_input}
TASK: {mode_tasks[mode]}

Remember: Consider the full conversation context when processing this input."""

    def validate_json(self, data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate JSON data against a schema.

        Args:
            data: The data to validate
            schema: The JSON schema

        Returns:
            The validated data

        Raises:
            jsonschema.ValidationError: If validation fails
        """
        try:
            jsonschema.validate(instance=data, schema=schema)
            return data
        except jsonschema.ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise

    def get_mcp_tools_for_mode(self, mode: str) -> List[FunctionDeclaration]:
        """
        Get MCP tool declarations for a specific mode.

        Args:
            mode: The operation mode

        Returns:
            List of FunctionDeclaration objects for allowed tools
        """
        allowed_tool_names = self.tools.get(mode, [])

        # Define all available tools
        all_tools = {
            "search_products": FunctionDeclaration(
                name="search_products",
                description="Search supplier products by description or specifications",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term for products",
                        },
                        "supplier_name": {
                            "type": "string",
                            "description": "Optional supplier name to filter by",
                        },
                    },
                    "required": ["query"],
                },
            ),
            "get_pricing_for_material": FunctionDeclaration(
                name="get_pricing_for_material",
                description="Get pricing information for specific materials",
                parameters={
                    "type": "object",
                    "properties": {
                        "material_type": {
                            "type": "string",
                            "description": "Type of material (e.g., steel, aluminum)",
                        },
                        "dimensions": {
                            "type": "string",
                            "description": "Optional dimensions like '4x8'",
                        },
                    },
                    "required": ["material_type"],
                },
            ),
            "compare_suppliers": FunctionDeclaration(
                name="compare_suppliers",
                description="Compare pricing across different suppliers for a specific material",
                parameters={
                    "type": "object",
                    "properties": {
                        "material_query": {
                            "type": "string",
                            "description": "Material to compare prices for (e.g., 'steel angle')",
                        },
                    },
                    "required": ["material_query"],
                },
            ),
        }

        # Return only the tools allowed for this mode
        return [all_tools[name] for name in allowed_tool_names if name in all_tools]

    def infer_mode(self, user_input: str) -> Tuple[str, float]:
        """
        Infer the most likely mode from user input.

        Args:
            user_input: The user's input text

        Returns:
            Tuple of (mode, confidence) where confidence is 0.0 to 1.0
        """
        input_lower = user_input.lower()

        # Mode indicators with weights
        mode_indicators = {
            "CALC": {
                "keywords": [
                    "area",
                    "yield",
                    "sheets",
                    "nest",
                    "dimensions",
                    "qty",
                    "quantity",
                    "size",
                    "cut",
                    "kerf",
                    "offcut",
                ],
                "weight": 0,
            },
            "PRICE": {
                "keywords": [
                    "price",
                    "cost",
                    "supplier",
                    "quote",
                    "sku",
                    "pricing",
                    "material",
                    "stock",
                    "lead time",
                    "delivery",
                ],
                "weight": 0,
            },
            "TABLE": {
                "keywords": [
                    "table",
                    "summary",
                    "total",
                    "final",
                    "markdown",
                    "invoice",
                    "breakdown",
                    "grand total",
                ],
                "weight": 0,
            },
        }

        # Calculate weights based on keyword matches
        for mode, info in mode_indicators.items():
            for keyword in info["keywords"]:
                if keyword in input_lower:
                    info["weight"] += 1

        # Find mode with highest weight
        max_weight = 0
        selected_mode = "CALC"  # Default
        for mode, info in mode_indicators.items():
            if info["weight"] > max_weight:
                max_weight = info["weight"]
                selected_mode = mode

        # Calculate confidence (0-1 scale)
        sum(len(info["keywords"]) for info in mode_indicators.values())
        confidence = min(max_weight / 3, 1.0) if max_weight > 0 else 0.0

        logger.info(f"Inferred mode: {selected_mode} (confidence: {confidence:.2f})")
        return selected_mode, confidence

    def run(
        self, mode: str, user_input: str, job: Optional[Job] = None, gemini_client=None, chat_history=None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Execute a mode with the given input.

        Args:
            mode: The operation mode (CALC, PRICE, or TABLE)
            user_input: User's input text
            job: Optional Job instance for context
            gemini_client: Optional Gemini client for API calls
            chat_history: Optional list of previous messages in Gemini format

        Returns:
            Tuple of (response_data, has_questions)

        Raises:
            ValueError: If mode is invalid
            jsonschema.ValidationError: If response doesn't match schema
        """
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {self.MODES}")

        logger.info(f"Running mode {mode} with input: {user_input[:100]}...")

        # Prepare job context if available
        job_ctx = None
        if job:
            job_ctx = {
                "job_number": job.job_number,
                "client": job.client.name if job.client else "N/A",
                "description": job.description or "",
            }

        # Get schema and tools for this mode
        schema = self.schemas[mode]
        allowed_tools = self.get_mcp_tools_for_mode(mode)

        # Render the prompt
        prompt = self.render_prompt(mode, user_input, job_ctx, schema)

        # Gemini client is required
        if gemini_client is None:
            raise ValueError("Gemini client is required")

        # Configure Gemini with mode-specific settings
        gemini_client.system_instruction = self.get_system_prompt()

        # Make the API call with JSON output enforced
        import google.generativeai as genai

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json"
        )

        # Start chat with history if provided
        if chat_history:
            logger.debug(f"Starting chat with {len(chat_history)} history messages")
            chat = gemini_client.start_chat(history=chat_history)
        else:
            logger.debug("Starting fresh chat session (no history)")
            chat = gemini_client.start_chat()
            
        response = chat.send_message(
            prompt, tools=allowed_tools, generation_config=generation_config
        )

        # Parse JSON response
        response_text = response.text
        logger.debug(f"Raw response from Gemini: {response_text[:500]}...")
        response_data = json.loads(response_text)

        # Validate against schema
        validated_data = self.validate_json(response_data, schema)

        # Check for questions
        questions = validated_data.get("questions", [])
        has_questions = len(questions) > 0

        if has_questions:
            logger.info(f"Mode {mode} has {len(questions)} clarifying questions")
        else:
            logger.info(f"Mode {mode} completed successfully with no questions")

        return validated_data, has_questions
