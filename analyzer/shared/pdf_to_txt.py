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
import json

# Constants
MIN_TEXT_LENGTH_THRESHOLD = 32
LLM_MODEL = "gemini/gemini-3-flash-preview"
# LLM_MODEL = "gemini/gemini-2.5-flash"
# LLM_MODEL = "gemini/gemini-3-pro-preview"
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

def process_images_with_llm(images):
    """
    Sends a list of images to the LLM for OCR.
    images: List of dictionaries with keys 'mime_type' and 'data' (base64 string).
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Convert the content of the following image(s) into Markdown text. Combine the text from all images into a single coherent document. At the beginning of the document add a line 'OCR_accurracy: A%' where A may have values 'HIGH', 'MEDIUM', 'LOW' or 'VERY_LOW' based on the readability of the text in input images."}
            ]
        }
    ]

    for img in images:
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{img['mime_type']};base64,{img['data']}"
            }
        })

    print(f"Info: Sending {len(images)} page images to {LLM_MODEL} for OCR.", file=sys.stderr)
    response = litellm.completion(model=LLM_MODEL, messages=messages)

    # Log cost and token usage
    cost = litellm.completion_cost(completion_response=response)
    print(f"LLM_cost: {json.dumps({'cost': cost})}")
    
    usage = response.usage
    usage_info = {
        "input": getattr(usage, "prompt_tokens", 0),
        "output": getattr(usage, "completion_tokens", 0),
        "total": getattr(usage, "total_tokens", 0)
    }
    # Add cached tokens if available
    if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
            usage_info["cached"] = getattr(usage.prompt_tokens_details, "cached_tokens", 0)
    elif hasattr(usage, "cache_read_input_tokens"):
            usage_info["cached"] = usage.cache_read_input_tokens
    
    print(f"LLM_tokens: {json.dumps(usage_info)}")
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
    
    print("Info: Received OCR text from LLM.", file=sys.stderr)
    return llm_text_cleaned.strip()

def extract_text_from_jpg(jpg_path):
    """
    Extracts text content from a JPG file using LLM OCR.
    """
    try:
        with open(jpg_path, "rb") as f:
            img_bytes = f.read()
        
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        images = [{'mime_type': 'image/jpeg', 'data': base64_image}]
        return process_images_with_llm(images)

    except FileNotFoundError:
        raise RuntimeError(f"Error: Input JPG file not found at {jpg_path}")
    except Exception as e:
        raise RuntimeError(f"Error extracting text from JPG: {e}")
    except litellm.exceptions.APIConnectionError as e:
        raise RuntimeError(f"LLM Error: Could not connect to the API. {e}")

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
            
            images = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                # Render page to an image (pixmap)
                pix = page.get_pixmap(dpi=IMAGE_DPI)
                img_bytes = pix.tobytes(IMAGE_FORMAT)

                # Encode image bytes as base64
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                images.append({'mime_type': f'image/{IMAGE_FORMAT}', 'data': base64_image})

            return process_images_with_llm(images)
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
    parser = argparse.ArgumentParser(description="Extracts text from PDF or JPG")
    parser.add_argument("input_file", help="Input PDF or JPG file path")

    args = parser.parse_args()
    input_file = args.input_file
    
    if input_file.lower().endswith(".pdf"):
        text = extract_text_from_pdf(input_file)
    elif input_file.lower().endswith((".jpg", ".jpeg")):
        text = extract_text_from_jpg(input_file)
    else:
        print(f"Error: Unsupported file extension for {input_file}. Only .pdf and .jpg/.jpeg are supported.", file=sys.stderr)
        sys.exit(1)
        
    print(text)

    
if __name__ == "__main__":
    main()