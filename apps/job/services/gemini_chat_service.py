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
from typing import Any, Dict, List

import google.generativeai as genai
from django.db import transaction

# Correct import path for Part helper used to send function responses
from google.generativeai.protos import Part  # For building function responses
from google.generativeai.types import FunctionDeclaration

from apps.job.models import Job, JobQuoteChat
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.workflow.enums import AIProviderTypes
from apps.workflow.models import AIProvider

logger = logging.getLogger(__name__)


class GeminiChatService:
    """
    Service for handling AI chat responses using Gemini with tool integration.
    """

    def __init__(self) -> None:
        self.quoting_tool = QuotingTool()
        self.query_tool = SupplierProductQueryTool()

    def get_gemini_client(self) -> genai.GenerativeModel:
        """
        Configures and returns a Gemini client based on the default AIProvider.
        """
        try:
            ai_provider = AIProvider.objects.filter(
                provider_type=AIProviderTypes.GOOGLE,
                default=True,
            ).first()

            if not ai_provider:
                raise ValueError(
                    "No default Gemini AI provider configured. "
                    "Please add an AIProvider with type 'Gemini' and mark it as "
                    "default."
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

            return genai.GenerativeModel(
                model_name=model_name,
                tools=self._get_mcp_tools(),
            )

        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise

    def _get_system_prompt(self, job: Job) -> str:
        """Generate system prompt with job context for Gemini."""
        return f"""You are an intelligent quoting assistant for Morris Sheetmetal Works,
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

    @transaction.atomic
    def generate_ai_response(self, job_id: str, user_message: str) -> JobQuoteChat:
        """
        Generates an AI response using the Gemini API and MCP tools.
        This method handles the entire conversation flow, including tool calls.
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
