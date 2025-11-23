# Uses fits (PyMuPDF) for extracting text directly from pdf when possible
# and fallbacks to Gemini OCR for scanned documents

import argparse
import os
import sys
import fitz  # PyMuPDF library
import litellm
import base64
import io
import traceback

# Constants
MIN_TEXT_LENGTH_THRESHOLD = 32
LLM_MODEL = "gemini/gemini-2.5-flash"
# LLM_MODEL = "gemini/gemini-2.5-pro" # Lepsie pre rukou pisane dokumenty
IMAGE_FORMAT = "png" # Format for image conversion
IMAGE_DPI = 150 # Resolution for image conversion

def is_garbled_text(text: str, threshold: float = 0.3) -> bool:
    """
    Heuristically determines if the text is garbled.
    Checks for a high proportion of replacement characters or non-printable characters.
    """
    if not text:
        return False # Not garbled if empty

    garbled_chars = 0
    total_chars = len(text)

    # Characters to ignore in the garbled check (common whitespace)
    allowed_control_chars = {'\n', '\r', '\t'}

    for char in text:
        # Check for replacement character, private use areas, or other control characters
        if (char == '\ufffd' or                               # Official replacement character
            '\uE000' <= char <= '\uF8FF' or                   # Private Use Area
            (char.isprintable() is False and char not in allowed_control_chars)):
            garbled_chars += 1

    # If more than `threshold` of the text consists of these characters, consider it garbled.
    return (garbled_chars / total_chars) > threshold

def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from a PDF file.
    If the extracted text is shorter than MIN_TEXT_LENGTH_THRESHOLD,
    it falls back to converting pages to images and using an LLM for OCR.
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()

        text_is_garbled = is_garbled_text(text.strip())
        # Check if the extracted text is too short
        if len(text.strip()) < MIN_TEXT_LENGTH_THRESHOLD or text_is_garbled:
            reason = "garbled" if text_is_garbled else f"too short ({len(text.strip())} chars)"
            print(f"Info: Fitz extracted text is {reason}. Falling back to LLM OCR.", file=sys.stderr)
            llm_text = ""
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Convert the content of the following image(s) (pages from a PDF document) into Markdown text. Combine the text from all pages into a single coherent document."}
                    ]
                }
            ]

            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                # Render page to an image (pixmap)
                pix = page.get_pixmap(dpi=IMAGE_DPI)
                img_bytes = pix.tobytes(IMAGE_FORMAT)

                # Encode image bytes as base64
                base64_image = base64.b64encode(img_bytes).decode('utf-8')

                # Add image to the message content list
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{IMAGE_FORMAT};base64,{base64_image}"
                    }
                })

            # Call LLM with all images
            print(f"Info: Sending {doc.page_count} page images to {LLM_MODEL} for OCR.", file=sys.stderr)
            response = litellm.completion(model=LLM_MODEL, messages=messages)
            # Get raw text and strip leading/trailing whitespace
            llm_text_raw = response.choices[0].message.content.strip()
            # Remove potential markdown fences
            if llm_text_raw.startswith("```markdown"):
                 llm_text_cleaned = llm_text_raw.removeprefix("```markdown").strip()
            elif llm_text_raw.startswith("```"):
                 llm_text_cleaned = llm_text_raw.removeprefix("```").strip()
            else:
                 llm_text_cleaned = llm_text_raw
            # Remove trailing fence
            if llm_text_cleaned.endswith("```"):
                llm_text_cleaned = llm_text_cleaned.removesuffix("```").strip()
            llm_text = llm_text_cleaned # Use the cleaned text
            print("Info: Received OCR text from LLM.", file=sys.stderr)
            return llm_text.strip()
        else:
            print("text extracted via fitz")
            return text.strip()

    except FileNotFoundError:
        raise RuntimeError(f"Error: Input PDF file not found at {pdf_path}")
    except Exception as e:
        raise RuntimeError(f"Error extracting text from PDF: {e}")
    except litellm.exceptions.APIConnectionError as e:
        raise RuntimeError(f"LLM Error: Could not connect to the API. {e}")

def main():
    parser = argparse.ArgumentParser(description="Extracts text from PDF")
    parser.add_argument("pdf", help="Input PDF file path")

    args = parser.parse_args()
    text = extract_text_from_pdf(args.pdf)
    print(text)

    
if __name__ == "__main__":
    main()