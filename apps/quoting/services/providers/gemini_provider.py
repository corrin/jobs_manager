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

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
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
                logger.error("Gemini API key not provided")
                raise ValueError("Gemini API key not provided")

            logger.info(f"Initializing Gemini client with model: {self.model_name}")
            client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client initialized successfully")

            # File handling
            if not os.path.exists(file_path):
                logger.error(f"PDF file not found: {file_path}")
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            file_size = os.path.getsize(file_path)
            logger.info(f"Processing PDF with Gemini {self.model_name}, file size: {file_size} bytes")

            # Read and encode the PDF file
            logger.info("Reading PDF file...")
            with open(file_path, "rb") as file:
                file_content = file.read()

            logger.info(f"PDF content read, size: {len(file_content)} bytes")

            # Encode to base64
            logger.info("Encoding PDF to base64...")
            file_b64 = base64.b64encode(file_content).decode("utf-8")
            logger.info(f"Base64 encoding complete, length: {len(file_b64)} characters")

            # Create the extraction prompt
            logger.info("Creating extraction prompt...")
            prompt = create_extraction_prompt()
            logger.info(f"Prompt created, length: {len(prompt)} characters")

            # Prepare the content for Gemini
            contents = [
                {"text": prompt},
                {"inline_data": {"mime_type": "application/pdf", "data": file_b64}},
            ]
            logger.info(f"Content prepared for Gemini API call with {len(contents)} parts")

            # Call Gemini API
            logger.info(f"Calling Gemini API with model: {self.model_name}")
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={
                    "max_output_tokens": 819200, 
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            logger.info("Gemini API call completed successfully")
            
            # Save complete response to debug file
            self._save_debug_response(response, file_path)

            # Log token usage if available
            if hasattr(response, "usage"):
                log_token_usage(response.usage, "Gemini")
                logger.info(f"Token usage: {response.usage}")
            else:
                logger.warning("No usage information in response")

            # Comprehensive response logging
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

            # Check for any errors or issues in the response
            logger.info(f"Response has prompt_feedback: {hasattr(response, 'prompt_feedback')}")
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                logger.warning(f"Prompt feedback (potential issues): {response.prompt_feedback}")

            # Check if there are any safety issues or blocks
            logger.info(f"Response has candidates: {hasattr(response, 'candidates')}")
            if hasattr(response, "candidates"):
                if response.candidates:
                    logger.info(f"Candidates length: {len(response.candidates)}")
                    candidate = response.candidates[0]
                    logger.info(f"First candidate type: {type(candidate)}")
                    
                    if hasattr(candidate, "finish_reason"):
                        logger.info(f"Finish reason: {candidate.finish_reason}")
                        if candidate.finish_reason and candidate.finish_reason != "STOP":
                            logger.warning(f"Unexpected finish reason: {candidate.finish_reason}")

                    if hasattr(candidate, "safety_ratings"):
                        logger.info(f"Safety ratings: {candidate.safety_ratings}")

                    if hasattr(candidate, "blocked"):
                        logger.info(f"Candidate blocked: {candidate.blocked}")
                        if candidate.blocked:
                            logger.error("Candidate is blocked - content may have been filtered")
                else:
                    logger.error("Response has candidates attribute but candidates list is empty")
            else:
                logger.warning("Response has no candidates attribute")

            # Check for text attribute
            logger.info(f"Response has text attribute: {hasattr(response, 'text')}")
            if hasattr(response, "text"):
                logger.info(f"Response.text is None: {response.text is None}")
                logger.info(f"Response.text type: {type(response.text) if response.text is not None else 'None'}")
                if response.text:
                    logger.info(f"Response.text length: {len(response.text)}")
                    logger.info(f"Response.text preview: {response.text[:200]}...")
                else:
                    logger.error("Response.text is None or empty")

            # Extract text content from the response
            # With the newer google-genai library, response.text is the direct way to access content
            result_text = None
            
            if hasattr(response, "text") and response.text is not None:
                result_text = response.text
                logger.info("Successfully extracted text from response.text")
            else:
                logger.error("No text content found in response - response.text is None or missing")
                # Log response structure for debugging
                logger.error(f"Response type: {type(response)}")
                logger.error(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

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

    def _save_debug_response(self, response, file_path: str) -> None:
        """
        Save the complete Gemini API response to a debug file for troubleshooting.
        
        Args:
            response: The response object from Gemini API
            file_path: Original file path being processed
        """
        import datetime
        
        debug_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "source_file": os.path.basename(file_path),
            "model_name": self.model_name,
            "response_type": str(type(response)),
            "response_attributes": [attr for attr in dir(response) if not attr.startswith('_')],
        }
        
        # Try to serialize all response attributes
        for attr_name in debug_data["response_attributes"]:
            try:
                attr_value = getattr(response, attr_name)
                # Convert to JSON-serializable format
                if hasattr(attr_value, '__dict__'):
                    debug_data[attr_name] = str(attr_value)
                elif callable(attr_value):
                    debug_data[f"{attr_name}_callable"] = True
                else:
                    debug_data[attr_name] = attr_value
            except Exception as e:
                debug_data[f"{attr_name}_error"] = str(e)
        
        # Special handling for specific attributes
        if hasattr(response, 'text'):
            debug_data["text_is_none"] = response.text is None
            debug_data["text_length"] = len(response.text) if response.text else 0
            debug_data["text_preview"] = response.text[:500] if response.text else None
        
        if hasattr(response, 'candidates') and response.candidates:
            debug_data["candidates_count"] = len(response.candidates)
            candidate_details = []
            for i, candidate in enumerate(response.candidates):
                candidate_info = {
                    "index": i,
                    "type": str(type(candidate)),
                    "attributes": [attr for attr in dir(candidate) if not attr.startswith('_')]
                }
                # Add specific candidate details
                if hasattr(candidate, 'finish_reason'):
                    candidate_info["finish_reason"] = candidate.finish_reason
                if hasattr(candidate, 'blocked'):
                    candidate_info["blocked"] = candidate.blocked
                if hasattr(candidate, 'safety_ratings'):
                    candidate_info["safety_ratings"] = str(candidate.safety_ratings)
                if hasattr(candidate, 'content'):
                    candidate_info["has_content"] = candidate.content is not None
                    if candidate.content:
                        candidate_info["content_type"] = str(type(candidate.content))
                        if hasattr(candidate.content, 'parts'):
                            candidate_info["content_parts_count"] = len(candidate.content.parts) if candidate.content.parts else 0
                candidate_details.append(candidate_info)
            debug_data["candidates_details"] = candidate_details
        
        if hasattr(response, 'prompt_feedback'):
            debug_data["prompt_feedback"] = str(response.prompt_feedback)
        
        if hasattr(response, 'usage'):
            debug_data["usage"] = str(response.usage)
        
        # Save to debug file
        debug_file_path = "/tmp/gemini_response_debug.json"
        try:
            with open(debug_file_path, "w") as f:
                json.dump(debug_data, f, indent=2, default=str)
            logger.info(f"Complete Gemini response saved to {debug_file_path}")
        except Exception as e:
            logger.error(f"Failed to save debug response: {e}")
            # Try to save a minimal version
            try:
                minimal_debug = {
                    "timestamp": debug_data["timestamp"],
                    "error": "Failed to serialize full response",
                    "response_type": debug_data["response_type"],
                    "text_is_none": debug_data.get("text_is_none", "unknown"),
                    "has_candidates": hasattr(response, 'candidates'),
                    "serialization_error": str(e)
                }
                with open(debug_file_path, "w") as f:
                    json.dump(minimal_debug, f, indent=2)
                logger.info(f"Minimal debug response saved to {debug_file_path}")
            except Exception as e2:
                logger.error(f"Failed to save even minimal debug response: {e2}")
