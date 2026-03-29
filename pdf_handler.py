import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os


def fix_arabic(text):
    return get_display(text)

def pdf_to_images(pdf_path, dpi=200):
    print(f"   → Converting PDF pages to images...")
    doc = fitz.open(pdf_path)
    os.makedirs("input/pdf_pages", exist_ok=True)

    image_paths = []
    for page_num, page in enumerate(doc):
        scale  = fitz.Matrix(dpi / 72, dpi / 72)
        pixmap = page.get_pixmap(matrix=scale)
        path   = f"input/pdf_pages/page_{page_num}.jpg"
        pixmap.save(path)
        image_paths.append(path)
        print(f"   → Page {page_num + 1} saved as image")

    return image_paths


def extract_pdf_blocks(pdf_path):
    print(f"   → Extracting text blocks from PDF...")
    doc       = fitz.open(pdf_path)
    all_blocks = []

    for page_num, page in enumerate(doc):
        page_rect = page.rect
        blocks    = page.get_text("blocks")

        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            text = text.strip()
            if not text:
                continue

            all_blocks.append({
                "text":        fix_arabic(text),
                "raw_text":    text,
                "bbox":        [x0, y0, x1, y1],
                "page":        page_num,
                "page_width":  page_rect.width,
                "page_height": page_rect.height
            })

    print(f"   → Extracted {len(all_blocks)} text blocks from PDF")
    return all_blocks


def crop_region_from_pdf(pdf_path, bbox, page_num, output_path):

    doc  = fitz.open(pdf_path)
    page = doc[page_num]
    rect = fitz.Rect(
        bbox[0] - 5, 
        bbox[1] - 5,
        bbox[2] + 5,
        bbox[3] + 5
    )
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
    pix.save(output_path)
    return output_path