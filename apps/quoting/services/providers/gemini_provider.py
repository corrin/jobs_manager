import base64
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from google import genai

from .common import clean_json_response, create_extraction_prompt, log_token_usage

logger = logging.getLogger(__name__)


class GeminiPriceExtractionProvider:
    """Gemini AI provider for price extraction from PDF documents."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model_name = model_name

    def get_provider_name(self) -> str:
        return "Gemini"

    def extract_price_data(
        self, file_path: str, content_type: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract price data from a supplier price list PDF using Gemini 2.5 Flash.

        Args:
            file_path: Path to the PDF file
            content_type: MIME type of the file

        Returns:
            Tuple containing extracted data dict and error message if any
        """
        try:
            # Initialize the Gemini client
            if not self.api_key:
                raise ValueError("Gemini API key not provided")

            client = genai.Client(api_key=self.api_key)

            # File handling
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            logger.info(f"Processing PDF with Gemini {self.model_name}...")

            # Read and encode the PDF file
            with open(file_path, "rb") as file:
                file_content = file.read()

            # Encode to base64
            file_b64 = base64.b64encode(file_content).decode("utf-8")

            # Create the extraction prompt
            prompt = create_extraction_prompt()

            # Prepare the content for Gemini
            contents = [
                {"text": prompt},
                {"inline_data": {"mime_type": "application/pdf", "data": file_b64}},
            ]

            # Call Gemini API
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={
                    "max_output_tokens": 8000,
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )

            # Log token usage if available
            if hasattr(response, "usage"):
                log_token_usage(response.usage, "Gemini")

            # Check for any errors or issues in the response
            logger.info(
                f"Response has prompt_feedback: {hasattr(response, 'prompt_feedback')}"
            )
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                logger.info(f"Prompt feedback: {response.prompt_feedback}")

            # Check if there are any safety issues or blocks
            logger.info(f"Response has candidates: {hasattr(response, 'candidates')}")
            logger.info(
                f"Candidates length: {len(response.candidates) if hasattr(response, 'candidates') and response.candidates else 0}"
            )

            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                logger.info(
                    f"Candidate has finish_reason: {hasattr(candidate, 'finish_reason')}"
                )
                if hasattr(candidate, "finish_reason"):
                    logger.info(f"Finish reason: {candidate.finish_reason}")

                logger.info(
                    f"Candidate has safety_ratings: {hasattr(candidate, 'safety_ratings')}"
                )
                if hasattr(candidate, "safety_ratings"):
                    logger.info(f"Safety ratings: {candidate.safety_ratings}")

                # Also check if candidate is blocked
                if hasattr(candidate, "blocked"):
                    logger.info(f"Candidate blocked: {candidate.blocked}")

                # Check citation metadata
                if hasattr(candidate, "citation_metadata"):
                    logger.info(f"Citation metadata: {candidate.citation_metadata}")

                # Log all candidate attributes for debugging
                logger.info(
                    f"All candidate attributes: {[attr for attr in dir(candidate) if not attr.startswith('_')]}"
                )

            # Extract text content from the response
            result_text = None

            # Try different ways to get the text content
            if hasattr(response, "candidates") and response.candidates:
                # Get the first candidate
                candidate = response.candidates[0]
                logger.info(f"Candidate type: {type(candidate)}")
                logger.info(f"Candidate attributes: {dir(candidate)}")

                if hasattr(candidate, "content") and candidate.content:
                    content = candidate.content
                    logger.info(f"Content type: {type(content)}")
                    logger.info(f"Content attributes: {dir(content)}")

                    if hasattr(content, "parts"):
                        logger.info(f"Content parts: {content.parts}")
                        logger.info(
                            f"Content parts length: {len(content.parts) if content.parts else 0}"
                        )

                        if content.parts:
                            part = content.parts[0]
                            logger.info(f"Part type: {type(part)}")
                            logger.info(f"Part attributes: {dir(part)}")

                            if hasattr(part, "text"):
                                result_text = part.text
                                logger.info(
                                    "Successfully extracted text from part.text"
                                )
                            else:
                                logger.warning("Part has no text attribute")
                        else:
                            logger.warning("Content parts is empty")
                    else:
                        logger.warning("Content has no parts attribute")
                else:
                    logger.warning("Candidate has no content")
            elif hasattr(response, "text") and response.text is not None:
                result_text = response.text
                logger.info("Successfully extracted text from response.text")
            else:
                logger.error("No text content found in response")

            logger.info(
                f"Final result_text length: {len(result_text) if result_text else 0}"
            )
            logger.info(
                f"Result text preview: {result_text[:200] if result_text else 'None'}..."
            )

            if not result_text:
                return None, "Empty or no text content in Gemini API response"

            # Clean and parse the JSON response
            result_text = clean_json_response(result_text)

            try:
                extracted_data = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON response: {e}")
                logger.error(f"Raw response: {result_text[:500]}...")
                return None, f"Invalid JSON response from Gemini: {str(e)}"

            # Validate the response structure
            if not isinstance(extracted_data, dict):
                return None, "Invalid response format from Gemini"

            if "items" not in extracted_data:
                return None, "No items found in Gemini response"

            # Process and normalize the extracted data
            processed_data = self._process_extracted_data(extracted_data, file_path)

            logger.info(
                f"Successfully extracted {len(processed_data.get('items', []))} products using Gemini"
            )

            return processed_data, None

        except Exception as e:
            logger.exception(f"Error during Gemini PDF extraction: {e}")
            return None, str(e)

    def _process_extracted_data(
        self, raw_data: Dict[str, Any], file_path: str
    ) -> Dict[str, Any]:
        """
        Process and normalize the extracted data from Gemini.

        Args:
            raw_data: Raw data from Gemini API
            file_path: Original file path for reference

        Returns:
            Processed data in the expected format
        """
        # Ensure supplier information exists
        supplier_info = raw_data.get("supplier", {})
        if not supplier_info.get("name"):
            # Try to extract supplier name from filename or set default
            filename = os.path.basename(file_path)
            if "morris" in filename.lower():
                supplier_info["name"] = "Morris SM"
            else:
                supplier_info["name"] = "Unknown Supplier"

        # Process items
        items = raw_data.get("items", [])
        processed_items = []

        for item in items:
            if not isinstance(item, dict):
                continue

            # Ensure required fields exist
            processed_item = {
                "product_name": item.get("description", "").strip(),
                "description": item.get("description", "").strip(),
                "specifications": item.get("specifications", "").strip(),
                "item_no": item.get("supplier_item_code", "").strip(),
                "variant_id": item.get("variant_id", "").strip(),
                "unit_price": self._parse_price(item.get("unit_price")),
                "price_unit": "per unit",  # Default, could be enhanced
                "dimensions": item.get("dimensions", "").strip(),
                "metal_type": item.get("metal_type", "").strip(),
            }

            # Generate variant_id if not provided
            if not processed_item["variant_id"]:
                processed_item["variant_id"] = self._generate_variant_id(processed_item)

            # Only add items with valid data
            if (
                processed_item["product_name"]
                and processed_item["unit_price"] is not None
            ):
                processed_items.append(processed_item)

        # Create the final structured data
        structured_data = {
            "supplier": supplier_info,
            "items": processed_items,
            "parsing_stats": {
                "total_lines": len(str(raw_data).split("\n")),
                "items_found": len(processed_items),
                "pages_processed": 1,  # Gemini processes the entire PDF at once
                "extraction_method": "Gemini 2.5 Flash",
            },
        }

        return structured_data

    def _parse_price(self, price_value: Any) -> Optional[float]:
        """Parse price value from various formats."""
        if price_value is None:
            return None

        if isinstance(price_value, (int, float)):
            return float(price_value)

        if isinstance(price_value, str):
            # Remove currency symbols and whitespace
            cleaned = (
                price_value.replace("$", "").replace("£", "").replace("€", "").strip()
            )
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not parse price: {price_value}")
                return None

        return None

    def _generate_variant_id(self, item: Dict[str, Any]) -> str:
        """Generate a variant ID from item data."""
        parts = []

        # Use item code if available
        if item.get("item_no"):
            parts.append(item["item_no"])

        # Add key dimensions or specifications
        if item.get("dimensions"):
            # Extract key dimensions
            dims = (
                item["dimensions"].replace("mm", "").replace("m", "").replace(" ", "")
            )
            parts.append(dims[:20])  # Limit length

        # Use description as fallback
        if not parts and item.get("description"):
            desc_clean = item["description"].replace(" ", "_").replace("/", "_")[:30]
            parts.append(desc_clean)

        # Join parts and ensure it's not empty
        variant_id = "_".join(parts) if parts else "unknown"

        # Clean up the variant ID
        variant_id = "".join(c for c in variant_id if c.isalnum() or c in "_-")

        return variant_id[:100]  # Limit length
