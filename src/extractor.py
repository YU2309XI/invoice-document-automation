import io

import pymupdf
import pytesseract
from PIL import Image


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF.

    First tries normal PDF text extraction.
    If no usable text is found, automatically falls back to OCR.
    """

    document = pymupdf.open(pdf_path)

    # First attempt: normal text extraction
    pages = []

    for page in document:
        pages.append(page.get_text())

    text = "\n".join(pages).strip()

    if text:
        document.close()

        return text, "TEXT"

    # Fallback: OCR
    print("  No text layer detected. Running OCR...")

    ocr_pages = []

    for page in document:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2),
            alpha=False,
        )

        image = Image.open(
            io.BytesIO(pixmap.tobytes("png"))
        )

        ocr_text = pytesseract.image_to_string(
            image,
            config="--psm 6",
        )

        ocr_pages.append(ocr_text)

    document.close()

    return "\n".join(ocr_pages).strip(), "OCR"
