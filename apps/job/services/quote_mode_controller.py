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
        return """You are a quoting helper. Process requests in the specified MODE.
- MODE=CALC: Calculate quantities and dimensions. For sheet materials, use calc_sheet_tenths tool. MUST call emit_calc_result with your final results.
- MODE=PRICE: Search for materials and pricing. MUST call emit_price_result with your final results.
- MODE=TABLE: Format quote tables. MUST call emit_table_result with your final results.

CRITICAL: You MUST call the appropriate emit_[mode]_result tool to submit your final answer.
The emit tool call should contain ALL required fields according to the schema.
Make reasonable assumptions and explicitly state them in the 'assumptions' field.
Avoid asking questions - use sensible defaults (e.g., 3mm thickness, 304 stainless, open-top boxes).
Never call tools from the wrong mode."""

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
            "CALC": "Calculate required items from specifications. Call emit_calc_result with complete results including items list and assumptions.",
            "PRICE": "Search for materials using available tools, then call emit_price_result with normalized specs and pricing candidates.",
            "TABLE": "Format the quote data and call emit_table_result with rows, totals, and markdown table.",
        }

        return f"""MODE={mode}
SCHEMA for {mode}: {json.dumps(schema, indent=2)}{job_info}
CURRENT INPUT: {user_input}
TASK: {mode_tasks[mode]}

IMPORTANT: You MUST call emit_{mode.lower()}_result with your complete results.
Consider the full conversation context when processing this input."""

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

    def _proto_to_dict(self, obj: Any) -> Any:
        """
        Recursively convert protobuf/MapComposite objects to plain dicts.

        Args:
            obj: Object that might be a protobuf wrapper

        Returns:
            Plain Python object (dict, list, or primitive)
        """
        if obj is None:
            return None
        elif hasattr(obj, "__class__") and "MapComposite" in str(type(obj)):
            # This is a protobuf map wrapper - convert to dict
            result = {}
            for key in obj:
                result[key] = self._proto_to_dict(obj[key])
            return result
        elif hasattr(obj, "__class__") and "RepeatedComposite" in str(type(obj)):
            # This is a protobuf repeated wrapper - convert to list
            return [self._proto_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._proto_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._proto_to_dict(item) for item in obj]
        else:
            # Primitive type or already converted
            return obj

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove JSON Schema fields that Gemini doesn't support.
        Keep only: type, description, properties, required, items, enum

        Args:
            schema: Original JSON schema

        Returns:
            Cleaned schema compatible with Gemini
        """
        # Only these fields are safe for Gemini
        allowed_fields = {
            "type",
            "description",
            "properties",
            "required",
            "items",
            "enum",
        }

        def clean_dict(d: dict) -> dict:
            """Recursively clean dictionary keeping only allowed fields."""
            if not isinstance(d, dict):
                return d

            cleaned = {}
            for key, value in d.items():
                if key not in allowed_fields:
                    continue

                if key == "type":
                    # Handle nullable types - remove "null" from arrays
                    if isinstance(value, list):
                        non_null = [t for t in value if t != "null"]
                        cleaned[key] = non_null[0] if len(non_null) == 1 else non_null
                    else:
                        cleaned[key] = value

                elif key == "items":
                    # Gemini handles single-schema form best
                    if isinstance(value, list):
                        cleaned[key] = clean_dict(value[0]) if value else {}
                    else:
                        cleaned[key] = clean_dict(value)

                elif key == "properties":
                    cleaned[key] = {k: clean_dict(v) for k, v in value.items()}

                elif key == "enum":
                    # Limit enum size to prevent bloat (keep first 20)
                    cleaned[key] = value[:20] if len(value) > 20 else value

                elif isinstance(value, dict):
                    cleaned[key] = clean_dict(value)
                elif isinstance(value, list):
                    cleaned[key] = [
                        clean_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    cleaned[key] = value

            return cleaned

        return clean_dict(schema)

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
            "calc_sheet_tenths": FunctionDeclaration(
                name="calc_sheet_tenths",
                description="Calculate how many 'tenths' of a sheet a part occupies. Sheet divided into 5x2 grid (600x480mm sections for 1200x2400mm sheet). Returns number of sections needed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "part_width_mm": {
                            "type": "number",
                            "description": "Width of part in mm",
                        },
                        "part_height_mm": {
                            "type": "number",
                            "description": "Height of part in mm",
                        },
                        "sheet_width_mm": {
                            "type": "number",
                            "description": "Sheet width in mm (default 1200)",
                        },
                        "sheet_height_mm": {
                            "type": "number",
                            "description": "Sheet height in mm (default 2400)",
                        },
                    },
                    "required": ["part_width_mm", "part_height_mm"],
                },
            ),
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
            # Emit tools for structured output
            "emit_calc_result": FunctionDeclaration(
                name="emit_calc_result",
                description="Submit the final calculation results. Call this after calculating all required items.",
                parameters=self._clean_schema_for_gemini(self.schemas["CALC"]),
            ),
            "emit_price_result": FunctionDeclaration(
                name="emit_price_result",
                description="Submit the final pricing results. Call this after gathering all pricing information.",
                parameters=self._clean_schema_for_gemini(self.schemas["PRICE"]),
            ),
            "emit_table_result": FunctionDeclaration(
                name="emit_table_result",
                description="Submit the final formatted table. Call this after formatting the quote table.",
                parameters=self._clean_schema_for_gemini(self.schemas["TABLE"]),
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
        self,
        mode: str,
        user_input: str,
        job: Optional[Job] = None,
        gemini_client=None,
        chat_history=None,
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

        # Import Gemini components
        import google.generativeai as genai

        # Start chat with history if provided
        if chat_history:
            logger.debug(f"Starting chat with {len(chat_history)} history messages")
            chat = gemini_client.start_chat(history=chat_history)
        else:
            logger.debug("Starting fresh chat session (no history)")
            chat = gemini_client.start_chat()

        # Send initial message (no JSON format enforcement - tools handle structure)
        try:
            response = chat.send_message(prompt, tools=allowed_tools)
        except Exception as e:
            logger.error(f"Error sending initial message: {e}")
            logger.error(f"Full prompt:\n{prompt}")
            logger.error(f"Tools configured: {[t.name for t in allowed_tools]}")
            logger.error(
                f"Chat history length: {len(chat_history) if chat_history else 0}"
            )
            # Log the actual function declaration to see what Gemini rejects
            for tool in allowed_tools:
                logger.error(f"Tool {tool.name} parameters: {tool.parameters}")
            raise

        # Process response to find emit tool call
        emit_tool_name = f"emit_{mode.lower()}_result"
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Processing response iteration {iteration}")

            # Check if response contains tool calls
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_name = part.function_call.name
                        tool_args = (
                            dict(part.function_call.args)
                            if part.function_call.args
                            else {}
                        )

                        logger.info(f"Tool call detected: {tool_name}")

                        if tool_name == emit_tool_name:
                            # This is our terminal emit tool - extract and return results
                            logger.info(f"Emit tool called: {tool_name}")
                            logger.debug(f"Emit tool args type: {type(tool_args)}")

                            # Convert protobuf wrapper to plain dict
                            tool_args = self._proto_to_dict(tool_args)
                            logger.debug(f"Converted tool args: {tool_args}")

                            # Validate against schema
                            validated_data = self.validate_json(tool_args, schema)

                            # Check for questions
                            questions = validated_data.get("questions", [])
                            has_questions = len(questions) > 0

                            if has_questions:
                                logger.info(
                                    f"Mode {mode} has {len(questions)} clarifying questions"
                                )
                            else:
                                logger.info(
                                    f"Mode {mode} completed successfully with no questions"
                                )

                            return validated_data, has_questions

                        else:
                            # Execute intermediate tool (for PRICE mode)
                            logger.info(
                                f"Executing intermediate tool: {tool_name} with args: {tool_args}"
                            )
                            tool_result = self._execute_tool(tool_name, tool_args)

                            # Send tool result back to continue conversation
                            response = chat.send_message(
                                genai.protos.Content(
                                    parts=[
                                        genai.protos.Part(
                                            function_response=genai.protos.FunctionResponse(
                                                name=tool_name,
                                                response={"result": tool_result},
                                            )
                                        )
                                    ]
                                )
                            )
                            continue

            # Check if there's text content (model might be explaining or asking)
            try:
                text_content = response.text
                logger.debug(f"Model response text: {text_content[:200]}...")

                # If we're here and no emit tool was called, prompt for it
                if iteration == 1:
                    logger.info(
                        f"No emit tool called yet, prompting for {emit_tool_name}"
                    )
                    response = chat.send_message(
                        f"Please complete your analysis and call the {emit_tool_name} tool with your final results."
                    )
                else:
                    # Give model another chance
                    response = chat.send_message(
                        f"You must call {emit_tool_name} to submit your results. Please do so now."
                    )
            except Exception as e:
                logger.debug(f"No text in response (likely a tool call): {e}")
                # This is fine - might be a tool-only response

        # If we get here, something went wrong
        raise ValueError(
            f"Model did not call {emit_tool_name} after {max_iterations} attempts"
        )

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            String result from the tool execution
        """
        # Import the quoting tools
        from apps.quoting.mcp import QuotingTool

        try:
            quoting_tool = QuotingTool()
            tool_map = {
                "calc_sheet_tenths": quoting_tool.calc_sheet_tenths,
                "search_products": quoting_tool.search_products,
                "get_pricing_for_material": quoting_tool.get_pricing_for_material,
                "compare_suppliers": quoting_tool.compare_suppliers,
            }

            if tool_name in tool_map:
                result = tool_map[tool_name](**arguments)
                logger.debug(
                    f"Tool {tool_name} returned: {result[:500] if isinstance(result, str) else result}..."
                )
                return result
            elif tool_name.startswith("emit_"):
                # Emit tools don't need execution, they're terminal
                logger.debug(f"Emit tool {tool_name} doesn't require execution")
                return None
            else:
                logger.warning(f"Unknown tool requested: {tool_name}")
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return f"Error executing tool '{tool_name}': {str(e)}"
