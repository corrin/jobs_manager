"""
Integration Test Script for Claude Chat Functionality

This script provides a command-line interface to test the end-to-end
flow of the AI-powered quoting chat. It initializes the Django environment,
connects to the configured AI provider, sends a message, and displays
the response, including any tool usage.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.job.models import Job
from apps.job.services.mcp_chat_service import MCPChatService

# Configure basic logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to test the MCPChatService and Claude integration.

    This command sends a message to the chat service for a specific job
    and prints the AI's response, including any tool usage. It's a crucial
    tool for debugging the full AI interaction pipeline.

    Example usage:
    python manage.py test_claude_chat <job_id> "What is the price for 2mm steel sheet?"
    """

    help = "Tests the Claude chat functionality for a given job and message."

    def add_arguments(self, parser):
        """
        Add command line arguments for job_id and the message.
        """
        parser.add_argument(
            "job_id", type=str, help="The UUID of the job to test the chat with."
        )
        parser.add_argument(
            "message", type=str, help="The message to send to the AI assistant."
        )

    def handle(self, *args, **options):
        """
        The main logic of the command. It orchestrates the test by
        fetching the job, initializing the service, and calling the AI.
        """
        job_id = options["job_id"]
        user_message = options["message"]

        self.stdout.write(
            self.style.SUCCESS(
                f"--- Starting Claude Chat Test for Job ID: {job_id} ---"
            )
        )
        self.stdout.write(f"User Message: '{user_message}'")

        try:
            # 1. Verify the job exists
            self.stdout.write(f"Checking for job {job_id}...")
            job = Job.objects.get(id=job_id)
            self.stdout.write(self.style.SUCCESS(f"Found Job: {job.name}"))

            # 2. Instantiate the chat service
            self.stdout.write("Initializing MCPChatService...")
            chat_service = MCPChatService()
            self.stdout.write(self.style.SUCCESS("Service initialized."))

            # 3. Generate the AI response
            self.stdout.write(
                self.style.HTTP_INFO(
                    "Sending message to AI and waiting for response..."
                )
            )
            assistant_message = chat_service.generate_ai_response(
                job_id=job_id, user_message=user_message
            )

            # 4. Print the results
            self.stdout.write(self.style.SUCCESS("\n--- AI Response Received ---"))
            self.stdout.write(f"Message ID: {assistant_message.message_id}")
            self.stdout.write(f"Role: {assistant_message.role}")

            self.stdout.write("\n--- Content ---")
            self.stdout.write(assistant_message.content)
            self.stdout.write("--- End Content ---\n")

            if assistant_message.metadata and assistant_message.metadata.get(
                "tool_uses"
            ):
                self.stdout.write(self.style.SUCCESS("--- Tools Used ---"))
                for tool_use in assistant_message.metadata["tool_uses"]:
                    self.stdout.write(f"Tool: {tool_use.get('name')}")
                    self.stdout.write(f"Input: {tool_use.get('input')}")
                    self.stdout.write("---")
            else:
                self.stdout.write(
                    self.style.WARNING("No tools were used in this interaction.")
                )

            if assistant_message.metadata and assistant_message.metadata.get("error"):
                self.stderr.write(
                    self.style.ERROR(
                        f"An error was reported in the assistant message metadata: {assistant_message.metadata.get('error_message')}"
                    )
                )

        except Job.DoesNotExist:
            raise CommandError(f'Job with ID "{job_id}" does not exist.')
        except ValueError as e:
            # Catches configuration errors from the service, e.g., missing API key
            raise CommandError(f"Configuration Error: {e}")
        except Exception as e:
            logger.exception("An unexpected error occurred during the chat test.")
            raise CommandError(f"An unexpected error occurred: {e}")

        self.stdout.write(self.style.SUCCESS("\n--- Test Completed Successfully ---"))
