import argparse
import os
import sys
import fitz  # PyMuPDF library

def extract_text_from_pdf(pdf_path):
    """Extracts text content from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
        return text
    except FileNotFoundError:
        print(f"Error: Input PDF file not found at {pdf_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}", file=sys.stderr)
        sys.exit(1)
        

def main():
    parser = argparse.ArgumentParser(description="Extracts text from PDF")
    parser.add_argument("pdf", help="Input PDF file path")

    args = parser.parse_args()
    text = extract_text_from_pdf(args.pdf)
    print(text)

    
if __name__ == "__main__":
    main()