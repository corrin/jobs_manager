import base64
import json
import os

from mistralai import Mistral

# THIS FILE NEEDS FIXING.  print! erorr eating!
# Gross repeated breaches of architecture.


def encode_pdf(pdf_path):
    """Encode the PDF file to base64."""
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error encoding PDF: {str(e)}")
        return None


def main():
    try:
        # Initialize the client
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")

        client = Mistral(api_key=api_key)

        # File handling
        pdf_path = "Morris SM - Extrusions & Rolled Stock.pdf"
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        print("Processing PDF with Mistral OCR...")
        # Encode the PDF to base64
        base64_pdf = encode_pdf(pdf_path)
        if not base64_pdf:
            raise ValueError("Failed to encode PDF file")
        # Process the document with OCR
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            include_image_base64=True,
        )

        # Convert OCR response to a serializable dictionary
        # This function should be outside main or properly nested if it's a local helper
        # For now, assuming it's a helper function for the try block
        def ocr_response_to_dict(ocr_obj):
            if hasattr(ocr_obj, "__dict__"):
                return {k: ocr_response_to_dict(v) for k, v in ocr_obj.__dict__.items()}
            elif isinstance(ocr_obj, list):
                return [ocr_response_to_dict(item) for item in ocr_obj]
            else:
                return ocr_obj

        # Save the results to a JSON file
        json_output_file = "ocr_results.json"
        with open(json_output_file, "w") as f:
            json.dump(ocr_response_to_dict(ocr_response), f, indent=2)
        # Save the results to a Markdown file
        md_output_file = "ocr_results.md"
        with open(md_output_file, "w", encoding="utf-8") as f:
            if hasattr(ocr_response, "pages") and ocr_response.pages:
                for i, page in enumerate(ocr_response.pages, 1):
                    if hasattr(page, "markdown") and page.markdown:
                        f.write(f"# Page {i}\n\n")
                        f.write(page.markdown)
                        f.write("\n\n---\n\n")  # Add separator between pages
        print("\nOCR processing complete!")
        print(f"- JSON results saved to: {os.path.abspath(json_output_file)}")
        print(f"- Markdown results saved to: {os.path.abspath(md_output_file)}")
        # Print a preview of the results
        print("\nPreview of the OCR results (first page):")
        print("-" * 50)
        if hasattr(ocr_response, "pages") and ocr_response.pages:
            first_page = ocr_response.pages[0]
            print(f"\nPage 1 of {len(ocr_response.pages)}:")
            # Try to get markdown content first, fall back to text
            if hasattr(first_page, "markdown") and first_page.markdown:
                preview = first_page.markdown[:500]
                print(preview + ("..." if len(first_page.markdown) > 500 else ""))
            elif hasattr(first_page, "text") and first_page.text:
                preview = first_page.text[:500]
                print(preview + ("..." if len(first_page.text) > 500 else ""))
            else:
                print("No text content available for preview")
        else:
            print("No pages found in the OCR response.")
        print("\n" + "=" * 50)
        print("Full results have been saved to:")
        print(f"- {os.path.abspath(json_output_file)}")
        print(f"- {os.path.abspath(md_output_file)}")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        if "retry_after" in str(e).lower():
            print(
                "The server is processing your request. "
                " Please try again in a few moments."
            )


if __name__ == "__main__":
    main()
