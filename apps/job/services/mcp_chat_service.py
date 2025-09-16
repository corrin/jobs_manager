"""
MCP Chat Service

Handles AI-powered chat responses using the Model Context Protocol (MCP)
for accessing supplier data, pricing, and job context in chat conversations.

This service integrates:
- Existing AIProvider system for Claude API access
- MCP tools for supplier/pricing data access
- JobQuoteChat model for conversation persistence
- Streaming response support
"""

import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from anthropic import Anthropic
from anthropic.types import MessageParam, TextBlock
from django.db import transaction

from apps.job.models import Job, JobQuoteChat
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.workflow.enums import AIProviderTypes  # NEW
from apps.workflow.models import AIProvider, CompanyDefaults

logger = logging.getLogger(__name__)


class MCPChatService:
    """
    Service for handling AI chat responses with MCP tool integration.

    Connects the chat system to AI providers and MCP tools for intelligent
    responses about pricing, suppliers, and job context.
    """

    def __init__(self) -> None:
        self.quoting_tool = QuotingTool()
        self.query_tool = SupplierProductQueryTool()

    def get_claude_client(self) -> tuple[Anthropic, AIProvider]:
        """Get configured Claude client from AIProvider system."""
        try:
            # Look for the default Anthropic/Claude provider
            ai_provider = AIProvider.objects.filter(
                provider_type=AIProviderTypes.ANTHROPIC,
                default=True,
            ).first()

            if not ai_provider:
                raise ValueError(
                    "No default Claude AI provider configured. "
                    "Please add an AIProvider entry with provider_type='Claude' "
                    "and mark it as default."
                )

            if not ai_provider.api_key:
                raise ValueError(
                    "Claude AI provider is missing an API key. "
                    "Set the api_key field in the AIProvider record."
                )

            if not ai_provider.model_name:
                raise ValueError(
                    "Claude AI provider is missing a model name. "
                    "Set the model_name field in the AIProvider record."
                )

            return Anthropic(api_key=ai_provider.api_key), ai_provider

        except Exception as e:
            logger.error(f"Failed to get Claude client: {e}")
            raise

    def _get_system_prompt(self, job: Job) -> str:
        """Generate system prompt with job context and MCP tool descriptions."""
        company = CompanyDefaults.objects.first()
        return f"""You are an intelligent quoting assistant for {company.company_name},
a sheet metal jobbing shop.

Current Job Context:
- Job: {job.name}
- Client: {job.client.name}
- Status: {job.get_status_display()}
- Description: {job.description or 'No description available'}

You have access to the following tools to help with quoting and material sourcing:

1. **search_products**: Search supplier products by description or specifications
   - Use this to find specific materials or products
   - Example: search_products("steel sheet 4x8")

2. **get_pricing_for_material**: Get pricing information for specific materials \\
with dimensions
   - Use this to get current market pricing
   - Example: get_pricing_for_material("aluminum", "4x8")

3. **create_quote_estimate**: Create a detailed quote estimate for a job
   - Use this to generate comprehensive quotes with materials and labor
   - Example: create_quote_estimate("{job.id}", "steel sheet, welding", 10.5)

4. **get_supplier_status**: Check supplier information and scraping status
   - Use this to verify supplier availability and data freshness
   - Example: get_supplier_status("Evans Ltd")

5. **compare_suppliers**: Compare pricing across multiple suppliers for materials
   - Use this to find the best pricing options
   - Example: compare_suppliers("steel angle")

Always be helpful, professional, and specific in your responses. When providing
pricing or material recommendations, explain your reasoning and mention any relevant
supplier information."""

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Define MCP tools for Claude API."""
        return [
            {
                "name": "search_products",
                "description": "Search supplier products by description or specs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term for products",
                        },
                        "supplier_name": {
                            "type": "string",
                            "description": "Optional supplier name filter",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_pricing_for_material",
                "description": "Get pricing information for specific materials",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "material_type": {
                            "type": "string",
                            "description": "Type of material (e.g., steel, aluminum)",
                        },
                        "dimensions": {
                            "type": "string",
                            "description": "Optional dimensions specification",
                        },
                    },
                    "required": ["material_type"],
                },
            },
            {
                "name": "create_quote_estimate",
                "description": "Create a quote estimate for a job",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "Job ID to create quote for",
                        },
                        "materials": {
                            "type": "string",
                            "description": "Description of materials needed",
                        },
                        "labor_hours": {
                            "type": "number",
                            "description": "Estimated labor hours",
                        },
                    },
                    "required": ["job_id", "materials"],
                },
            },
            {
                "name": "get_supplier_status",
                "description": "Get status of supplier scraping and price lists",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "supplier_name": {
                            "type": "string",
                            "description": "Optional supplier name filter",
                        }
                    },
                },
            },
            {
                "name": "compare_suppliers",
                "description": "Compare pricing across suppliers for materials",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "material_query": {
                            "type": "string",
                            "description": "Material to compare prices for",
                        }
                    },
                    "required": ["material_query"],
                },
            },
        ]

    def _execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute MCP tool and return result."""
        try:
            if tool_name == "search_products":
                return self.quoting_tool.search_products(
                    arguments["query"], arguments.get("supplier_name") or ""
                )
            elif tool_name == "get_pricing_for_material":
                return self.quoting_tool.get_pricing_for_material(
                    arguments["material_type"], arguments.get("dimensions") or ""
                )
            elif tool_name == "create_quote_estimate":
                return self.quoting_tool.create_quote_estimate(
                    arguments["job_id"],
                    arguments["materials"],
                    arguments.get("labor_hours") or 0.0,
                )
            elif tool_name == "get_supplier_status":
                return self.quoting_tool.get_supplier_status(
                    arguments.get("supplier_name") or ""
                )
            elif tool_name == "compare_suppliers":
                return self.quoting_tool.compare_suppliers(arguments["material_query"])
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"MCP tool execution failed for {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    @transaction.atomic
    def generate_ai_response(
        self,
        job_id: str,
        user_message: str,
        stream_callback: Optional[Callable[..., None]] = None,
    ) -> JobQuoteChat:
        """
        Generate AI response using Claude with MCP tools.

        Args:
            job_id: UUID of the job for context
            user_message: User's message content
            stream_callback: Optional callback for streaming updates

        Returns:
            JobQuoteChat: The created assistant message
        """
        try:
            # Get job for context
            job = Job.objects.get(id=job_id)

            # Get recent chat history for context
            recent_messages = JobQuoteChat.objects.filter(job=job).order_by(
                "-timestamp"
            )[:10]

            # Build conversation history
            messages: List[MessageParam] = []
            for msg in reversed(recent_messages):
                messages.append({"role": msg.role, "content": msg.content})

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Get Claude client and AI provider
            client, ai_provider = self.get_claude_client()

            # Create assistant message for streaming
            assistant_message = JobQuoteChat.objects.create(
                job=job,
                message_id=f"assistant-{uuid.uuid4()}",
                role="assistant",
                content="",
                metadata={"streaming": True, "tool_uses": []},
            )

            # Make Claude API call with tools
            response = client.messages.create(
                model=ai_provider.model_name,
                max_tokens=4000,
                system=self._get_system_prompt(job),
                messages=messages,
                tools=self._get_mcp_tools(),
                stream=True,
            )

            # Process streaming response
            content_blocks = []
            current_content = ""
            tool_uses = []

            for chunk in response:
                if chunk.type == "content_block_start":
                    if chunk.content_block.type == "text":
                        content_blocks.append({"type": "text", "text": ""})
                    elif chunk.content_block.type == "tool_use":
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": chunk.content_block.id,
                                "name": chunk.content_block.name,
                                "input": "",
                            }
                        )

                elif chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        # Update text content
                        content_blocks[-1]["text"] += chunk.delta.text
                        current_content = "".join(
                            [
                                block.get("text", "")
                                for block in content_blocks
                                if block["type"] == "text"
                            ]
                        )

                        # Update message with streaming content
                        assistant_message.content = current_content
                        assistant_message.save(update_fields=["content"])

                        # Call stream callback if provided
                        if stream_callback:
                            stream_callback(assistant_message)

                    elif chunk.delta.type == "input_json_delta":
                        # Accumulate tool input
                        if "input" not in content_blocks[-1]:
                            content_blocks[-1]["input"] = ""
                        content_blocks[-1]["input"] += chunk.delta.partial_json

                elif chunk.type == "content_block_stop":
                    # Process completed tool use
                    if (
                        content_blocks
                        and content_blocks[-1]["type"] == "tool_use"
                        and "input" in content_blocks[-1]
                    ):
                        tool_block = content_blocks[-1]
                        try:
                            tool_input = json.loads(tool_block["input"])
                            tool_result = self._execute_mcp_tool(
                                tool_block["name"], tool_input
                            )

                            tool_uses.append(
                                {
                                    "name": tool_block["name"],
                                    "input": tool_input,
                                    "result": tool_result,
                                }
                            )

                            # Add tool result to conversation for Claude
                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "tool_use",
                                            "id": tool_block["id"],
                                            "name": tool_block["name"],
                                            "input": tool_input,
                                        }
                                    ],
                                }
                            )
                            messages.append(
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": tool_block["id"],
                                            "content": tool_result,
                                        }
                                    ],
                                }
                            )

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse tool input: {e}")

            # If tools were used, make another call for final response
            if tool_uses:
                final_response = client.messages.create(
                    model=ai_provider.model_name,
                    max_tokens=4000,
                    system=self._get_system_prompt(job),
                    messages=messages,
                    tools=self._get_mcp_tools(),
                )

                if final_response.content:
                    for block in final_response.content:
                        if isinstance(block, TextBlock):
                            current_content += block.text

            # Update final message
            assistant_message.content = current_content
            assistant_message.metadata = {
                "streaming": False,
                "tool_uses": tool_uses,
                "model": ai_provider.model_name,
            }
            assistant_message.save()

            return assistant_message

        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            # Create error message
            error_message = JobQuoteChat.objects.create(
                job=job,
                message_id=f"assistant-error-{uuid.uuid4()}",
                role="assistant",
                content=(
                    "I apologize, but I encountered an error processing your request:"
                    f"{str(e)}"
                ),
                metadata={"error": True, "error_message": str(e)},
            )
            return error_message
