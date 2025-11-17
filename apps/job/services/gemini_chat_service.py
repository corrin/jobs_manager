"""
Gemini Chat Service

Handles AI-powered chat responses using Google's Gemini API and integrates
with the application's internal tools (MCP - Model Context Protocol).

This service replaces the Claude-based implementation and provides a
seamless way to generate intelligent, context-aware responses for quoting.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from django.db import transaction

# Correct import path for Part helper used to send function responses
from google.generativeai.types import FunctionDeclaration

from apps.job.models import Job, JobQuoteChat
from apps.job.services.chat_file_service import ChatFileService
from apps.job.services.quote_mode_controller import QuoteModeController
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.workflow.enums import AIProviderTypes
from apps.workflow.models import AIProvider, CompanyDefaults

logger = logging.getLogger(__name__)


class GeminiChatService:
    """
    Service for handling AI chat responses using Gemini with tool integration.
    """

    def __init__(self) -> None:
        self.quoting_tool = QuotingTool()
        self.query_tool = SupplierProductQueryTool()
        self.mode_controller = QuoteModeController()
        self.file_service = ChatFileService()

    def start_conversation(self) -> None:
        """Configure Gemini API for this chat session."""
        ai_provider = AIProvider.objects.filter(
            provider_type=AIProviderTypes.GOOGLE
        ).first()

        if not ai_provider:
            raise ValueError("No Gemini AI provider configured in the database")

        if not ai_provider.api_key:
            raise ValueError("Gemini AI provider is missing an API key")

        genai.configure(api_key=ai_provider.api_key)
        logger.info("Gemini API configured for chat session")

    def get_gemini_client(self, mode: Optional[str] = None) -> genai.GenerativeModel:
        """
        Configures and returns a Gemini client based on the default AIProvider.
        """
        try:
            ai_provider = AIProvider.objects.filter(
                provider_type=AIProviderTypes.GOOGLE
            ).first()

            if not ai_provider:
                raise ValueError(
                    "No Gemini AI provider configured. "
                    "Please add an AIProvider with type 'Gemini'."
                )

            if not ai_provider.api_key:
                raise ValueError(
                    "Gemini AI provider is missing an API key. "
                    "Please set the api_key in the AIProvider record."
                )

            if not ai_provider.model_name:
                raise ValueError(
                    "Gemini AI provider is missing a model name. "
                    "Please set the model_name in the AIProvider record."
                )

            genai.configure(api_key=ai_provider.api_key)

            model_name = ai_provider.model_name

            # Get tools based on mode if provided
            if mode:
                tools = self.mode_controller.get_mcp_tools_for_mode(mode)
            else:
                tools = self._get_mcp_tools()

            return genai.GenerativeModel(
                model_name=model_name,
                tools=tools,
            )

        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise

    def _get_system_prompt(self, job: Job) -> str:
        """Generate system prompt with job context for Gemini."""
        company = CompanyDefaults.objects.first()
        return f"""You are an intelligent quoting assistant for {company.company_name},
a custom metal fabrication business. Your role is to help estimators create accurate
quotes by using the available tools to find material pricing, compare suppliers,
and generate estimates.

Current Job Context:
- Job: {job.name} (#{job.job_number})
- Job ID: {job.id}
- Client: {job.client.name}
- Status: {job.get_status_display()}
- Description: {job.description or 'No description available'}

Always be helpful, professional, and specific in your responses. When providing
pricing or material recommendations, explain your reasoning and mention any relevant
supplier information. Use the tools provided to answer user queries about products,
pricing, and suppliers."""

    def _get_mcp_tools(self) -> List[FunctionDeclaration]:
        """Define MCP tools for the Gemini API using FunctionDeclaration."""
        return [
            FunctionDeclaration(
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
            FunctionDeclaration(
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
            FunctionDeclaration(
                name="create_quote_estimate",
                description=(
                    "Create a quote estimate for a job, including materials and labor"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": (
                                "The UUID of the job to create the quote for"
                            ),
                        },
                        "materials": {
                            "type": "string",
                            "description": "A description of the materials needed",
                        },
                        "labor_hours": {
                            "type": "number",
                            "description": "Estimated labor hours",
                        },
                    },
                    "required": ["job_id", "materials"],
                },
            ),
            FunctionDeclaration(
                name="get_supplier_status",
                description="Get the status of supplier data scraping and price lists",
                parameters={
                    "type": "object",
                    "properties": {
                        "supplier_name": {
                            "type": "string",
                            "description": "Optional supplier name to filter by",
                        },
                    },
                },
            ),
            FunctionDeclaration(
                name="compare_suppliers",
                description=(
                    "Compare pricing across different suppliers for a specific material"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "material_query": {
                            "type": "string",
                            "description": (
                                "Material to compare prices for (e.g., 'steel angle')"
                            ),
                        },
                    },
                    "required": ["material_query"],
                },
            ),
        ]

    def _execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute an MCP tool by name and return its string output."""
        try:
            tool_map = {
                "search_products": self.quoting_tool.search_products,
                "get_pricing_for_material": self.quoting_tool.get_pricing_for_material,
                "create_quote_estimate": self.quoting_tool.create_quote_estimate,
                "get_supplier_status": self.quoting_tool.get_supplier_status,
                "compare_suppliers": self.quoting_tool.compare_suppliers,
            }
            if tool_name in tool_map:
                return tool_map[tool_name](**arguments)
            return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"MCP tool execution failed for {tool_name}: {e}")
            return f"Error executing tool '{tool_name}': {str(e)}"

    # ---------------------------------------------------------------------
    # Role Conversion Helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _to_gemini_role(db_role: str) -> str:
        """
        Convert roles stored in the database (`user`, `assistant`) to the
        role names expected by the Gemini API (`user`, `model`).

        Args:
            db_role: Role string from `JobQuoteChat.role`.

        Returns:
            A valid Gemini role string.
        """
        return "model" if db_role == "assistant" else "user"

    def _add_context_for_mode_transition(
        self, chat_history: list, current_mode: str
    ) -> list:
        """
        Add a synthetic context message when transitioning to PRICE mode.

        This injects previous CALC results as a structured "CONTEXT" message
        so the model doesn't re-ask for information already provided.

        Args:
            chat_history: Current chat history
            current_mode: The mode being entered

        Returns:
            Enhanced chat history with context message if applicable
        """
        # Only add context when transitioning to PRICE mode
        if current_mode != "PRICE":
            return chat_history

        # Extract recent calculation results from assistant messages
        recent_context_parts = []
        for msg in chat_history[-6:]:  # Look at last 6 messages
            if msg.get("role") == "model":
                for part in msg.get("parts", []):
                    if isinstance(part, str):
                        # Look for calculation results or material specifications
                        if any(
                            keyword in part.lower()
                            for keyword in [
                                "calculation",
                                "flat pattern",
                                "dimensions",
                                "thickness",
                                "material",
                                "quantity",
                            ]
                        ):
                            recent_context_parts.append(part)

        # If no relevant context found, don't inject anything
        if not recent_context_parts:
            return chat_history

        # Create a synthetic context message
        context_text = (
            "CONTEXT FROM PREVIOUS CONVERSATION:\n\n"
            + "\n\n".join(recent_context_parts)
            + "\n\n"
            "Use the above information to answer the pricing request. "
            "Do not re-ask for details already provided above."
        )

        context_msg = {"role": "user", "parts": [context_text]}

        # Insert context message before the final user message
        enhanced = chat_history.copy()
        enhanced.append(context_msg)

        logger.info(f"Injected context message for {current_mode} mode transition")
        logger.debug(f"Context message preview: {context_text[:200]}...")

        return enhanced

    @transaction.atomic
    def generate_ai_response(
        self, job_id: str, user_message: str, mode: Optional[str] = None
    ) -> JobQuoteChat:
        """
        Generates an AI response using the Gemini API and MCP tools.

        Args:
            job_id: The UUID of the job
            user_message: The user's message
            mode: Optional mode (CALC, PRICE, TABLE) for mode-based operation

        Returns:
            JobQuoteChat instance with the AI response
        """
        logger.info(
            f"Starting AI response generation for job {job_id} with "
            f"message: {user_message}"
        )
        try:
            job = Job.objects.get(id=job_id)
            logger.debug(f"Retrieved job: {job.name} (#{job.job_number})")

            model = self.get_gemini_client()
            logger.info(f"Gemini client configured with model: {model.model_name}")
            logger.debug(f"Tools configured for model: {self._get_mcp_tools()}")

            # -----------------------------------------------------------------
            # Initialise tool metadata tracking
            # -----------------------------------------------------------------
            tool_definitions = self._get_mcp_tools()  # Available tools for this session
            tool_calls: List[Dict[str, Any]] = []  # Record of executed tool calls

            system_prompt = self._get_system_prompt(job)
            model.system_instruction = system_prompt
            logger.debug(f"System prompt set: {system_prompt}")

            # Build conversation history for the model
            chat_history = []
            recent_messages = JobQuoteChat.objects.filter(job=job).order_by(
                "timestamp"
            )[:20]
            logger.debug(
                f"Retrieved {len(recent_messages)} recent messages for context"
            )

            for msg in recent_messages:
                logger.debug(f"Adding to history: {msg.role} - {msg.content[:50]}...")
                chat_history.append(
                    {
                        # Gemini expects roles to be either "user" or "model"
                        "role": self._to_gemini_role(msg.role),
                        "parts": [msg.content],
                    }
                )

            # Keep a copy of the history for metadata
            history_for_metadata = chat_history.copy()

            # Start a chat session with history
            logger.debug(
                f"Starting chat session with {len(chat_history)} history messages"
            )
            logger.debug(f"Chat history being sent to Gemini: {chat_history}")
            chat = model.start_chat(history=chat_history)

            # Send the new user message
            logger.info(f"Sending message to Gemini: {user_message}")
            response = chat.send_message(user_message)
            logger.debug("Received initial response from Gemini")
            logger.debug(f"Raw response object: {response}")
            logger.debug(f"Response candidates: {response.candidates}")
            try:
                logger.debug(f"Response text: {response.text}")
            except ValueError as e:
                logger.debug(f"No text response available (likely function call): {e}")

            # Process tool calls if the model requests them
            tool_call_count = 0
            while True:
                # Locate the first part that contains a function call
                call_part = next(
                    (
                        p
                        for p in response.candidates[0].content.parts
                        if hasattr(p, "function_call") and p.function_call
                    ),
                    None,
                )

                if call_part is None:
                    # No further tool invocations requested
                    logger.info(
                        f"No more tool calls requested. Total tool calls made: "
                        f"{tool_call_count}"
                    )
                    break

                function_call = call_part.function_call
                tool_name: str = function_call.name
                # `args` may be `None` if no parameters supplied
                raw_args = function_call.args or {}
                tool_args: Dict[str, Any] = {k: v for k, v in raw_args.items()}

                tool_call_count += 1
                logger.info(
                    f"Tool call #{tool_call_count}: Executing {tool_name} with "
                    f"args: {tool_args}"
                )
                tool_result = self._execute_mcp_tool(tool_name, tool_args)
                logger.debug(f"Tool {tool_name} returned: {tool_result[:200]}...")

                # Record the tool invocation for metadata
                tool_calls.append(
                    {
                        "name": tool_name,
                        "arguments": tool_args,
                        "result_preview": tool_result[
                            :200
                        ],  # Store a preview to keep metadata small
                    }
                )

                # Send tool result back to the model
                logger.debug("Sending tool result back to Gemini")
                function_response = genai.protos.FunctionResponse(
                    name=tool_name, response={"result": tool_result}
                )
                part = genai.protos.Part(function_response=function_response)
                response = chat.send_message(part)
                logger.debug(f"Received response after tool call #{tool_call_count}")

            # The final response from the model
            final_content = response.text
            logger.info(
                f"Final response from Gemini (length: {len(final_content)}): "
                f"{final_content[:100]}..."
            )

            # -----------------------------------------------------------------
            # Ensure all metadata is JSON-serialisable before saving
            # -----------------------------------------------------------------
            # Convert FunctionDeclaration objects to plain dictionaries
            serialisable_tool_definitions = []
            for t in tool_definitions:
                try:
                    serialisable_tool_definitions.append(json.loads(t.to_json()))
                except Exception:
                    serialisable_tool_definitions.append(
                        {
                            "name": getattr(t, "name", str(t)),
                        }
                    )

            # Persist the assistant's final message
            logger.debug("Saving assistant message to database")
            assistant_message = JobQuoteChat.objects.create(
                job=job,
                message_id=f"assistant-{uuid.uuid4()}",
                role="assistant",
                content=final_content,
                metadata={
                    "model": model.model_name,
                    "system_prompt": system_prompt,
                    "user_message": user_message,
                    "chat_history": history_for_metadata,
                    "tool_definitions": serialisable_tool_definitions,
                    "tool_calls": tool_calls,
                },
            )
            logger.info(
                f"Successfully generated AI response for job {job_id}. "
                f"Message ID: {assistant_message.message_id}"
            )
            return assistant_message

        except Exception as e:
            logger.exception(
                f"Gemini AI response generation failed for job {job_id}: {e}"
            )
            # Create and return an error message to be displayed in the chat
            error_message = JobQuoteChat.objects.create(
                job=Job.objects.get(id=job_id),
                message_id=f"assistant-error-{uuid.uuid4()}",
                role="assistant",
                content=(
                    f"I apologize, but I encountered an error processing your "
                    f"request: {str(e)}"
                ),
                metadata={"error": True, "error_message": str(e)},
            )
            return error_message

    @transaction.atomic
    def generate_mode_response(
        self, job_id: str, user_message: str, mode: Optional[str] = None
    ) -> JobQuoteChat:
        """
        Generate a response using the mode-based system.

        Args:
            job_id: The UUID of the job
            user_message: The user's message
            mode: Optional mode override. If None, mode is inferred from input

        Returns:
            JobQuoteChat instance with the structured response
        """
        logger.info(f"Starting mode-based response for job {job_id}")

        try:
            job = Job.objects.get(id=job_id)

            # Build conversation history from database
            chat_history = []
            recent_messages = JobQuoteChat.objects.filter(job=job).order_by(
                "timestamp"
            )[:20]
            logger.debug(
                f"Retrieved {len(recent_messages)} recent messages for context"
            )

            # Extract all file IDs from chat history
            all_file_ids = self.file_service.extract_file_ids_from_chat_history(
                list(recent_messages)
            )

            # Fetch all files once if any were found
            job_files_dict = {}
            if all_file_ids:
                job_files = self.file_service.fetch_job_files(job_id, all_file_ids)
                logger.info(f"Found {len(job_files)} files attached to conversation")
                # Create a lookup dict for quick access
                job_files_dict = {str(f.id): f for f in job_files}

            for msg in recent_messages:
                logger.debug(f"Adding to history: {msg.role} - {msg.content[:50]}...")

                # Build parts list - start with the text content
                parts = [msg.content]

                # Check if this specific message has file attachments
                if msg.metadata and "file_ids" in msg.metadata:
                    message_file_ids = msg.metadata["file_ids"]
                    # Get the files for this specific message
                    message_files = [
                        job_files_dict[fid]
                        for fid in message_file_ids
                        if fid in job_files_dict
                    ]

                    if message_files:
                        # Build file contents for this message's files
                        file_contents = (
                            self.file_service.build_file_contents_for_gemini(
                                message_files
                            )
                        )
                        parts.extend(file_contents)
                        logger.debug(
                            f"Added {len(file_contents)} file contents to message"
                        )

                chat_history.append(
                    {
                        # Gemini expects roles to be either "user" or "model"
                        "role": self._to_gemini_role(msg.role),
                        "parts": parts,
                    }
                )

            # Infer mode if not provided
            if mode is None:
                # Get current mode from last assistant message
                current_mode = None
                for msg in reversed(list(recent_messages)):
                    if msg.role == "assistant" and msg.metadata:
                        current_mode = msg.metadata.get("mode")
                        if current_mode:
                            break

                mode = self.mode_controller.infer_mode(user_message, current_mode)
                logger.info(f"Inferred mode: {mode} (previous: {current_mode})")
            else:
                logger.info(f"Using explicit mode: {mode}")

            # Get mode-specific Gemini client
            model = self.get_gemini_client(mode=mode)
            model.system_instruction = self.mode_controller.get_system_prompt()

            # Inject context summary as a message if switching modes
            enhanced_history = self._add_context_for_mode_transition(chat_history, mode)

            # Run the mode controller with enhanced chat history
            response_data, has_questions = self.mode_controller.run(
                mode=mode,
                user_input=user_message,
                job=job,
                gemini_client=model,
                chat_history=enhanced_history,
            )

            # Format the response for display
            if has_questions:
                # Format questions as a bulleted list
                questions = response_data.get("questions", [])
                content = "I need some clarification:\n\n"
                for q in questions:
                    content += f"• {q}\n"
            else:
                # Format the results based on mode
                if mode == "CALC":
                    results = response_data.get("results", {})
                    content = "**Calculation Results:**\n\n"
                    for key, value in results.items():
                        label = key.replace("_", " ").title()
                        if isinstance(value, float):
                            content += f"• {label}: {value:.2f}\n"
                        else:
                            content += f"• {label}: {value}\n"

                elif mode == "PRICE":
                    candidates = response_data.get("candidates", [])
                    content = "**Material Options:**\n\n"
                    for i, candidate in enumerate(candidates, 1):
                        content += f"**Option {i}: {candidate['supplier']}**\n"
                        content += f"• SKU: {candidate['sku']}\n"
                        content += f"• Price: ${candidate['price_per_uom']:.2f}/{candidate['uom']}\n"
                        if candidate.get("lead_time_days"):
                            content += (
                                f"• Lead Time: {candidate['lead_time_days']} days\n"
                            )
                        if candidate.get("delivery"):
                            content += f"• Delivery: ${candidate['delivery']:.2f}\n"
                        if candidate.get("notes"):
                            content += f"• Notes: {candidate['notes']}\n"
                        content += "\n"

                elif mode == "TABLE":
                    markdown = response_data.get("markdown", "")
                    totals = response_data.get("totals", {})
                    content = markdown
                    if not content:
                        content = "**Quote Summary:**\n\n"
                        content += f"• Material: ${totals.get('material', 0):.2f}\n"
                        content += f"• Labour: ${totals.get('labour', 0):.2f}\n"
                        content += f"• Freight: ${totals.get('freight', 0):.2f}\n"
                        content += f"• Overheads: ${totals.get('overheads', 0):.2f}\n"
                        content += f"• Markup: {totals.get('markup_pct', 0)}%\n"
                        content += f"• **Total (ex GST): ${totals.get('grand_total_ex_gst', 0):.2f}**\n"

            # Save the response
            assistant_message = JobQuoteChat.objects.create(
                job=job,
                message_id=f"assistant-{uuid.uuid4()}",
                role="assistant",
                content=content,
                metadata={
                    "mode": mode,
                    "response_data": response_data,
                    "has_questions": has_questions,
                    "model": model.model_name,
                    "user_message": user_message,
                },
            )

            logger.info(f"Successfully generated mode-based response for job {job_id}")
            return assistant_message

        except Exception as e:
            logger.exception(f"Mode-based response generation failed: {e}")
            # Create error message
            error_message = JobQuoteChat.objects.create(
                job=Job.objects.get(id=job_id),
                message_id=f"assistant-error-{uuid.uuid4()}",
                role="assistant",
                content=f"I encountered an error processing your request: {str(e)}",
                metadata={"error": True, "error_message": str(e), "mode": mode},
            )
            return error_message
