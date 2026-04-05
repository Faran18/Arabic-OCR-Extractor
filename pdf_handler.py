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
    doc        = fitz.open(pdf_path)
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


def build_matched_pdf(source_pdf_path, matched_lines, output_path="output/result.pdf", padding=15):
    """
    Extract ALL matched lines as a single union region per source page,
    output as one clean PDF page sized exactly to that region.
    This preserves the exact vector formatting of the reference PDF.
    """
    os.makedirs("output", exist_ok=True)

    pdf_matches = [
        ln for ln in matched_lines
        if ln.get("match_score", 0) > 0 and "bbox" in ln and "page" in ln
    ]

    if not pdf_matches:
        print("   ⚠  No matched PDF blocks — skipping PDF export")
        return None

    # Group by source page
    pages = {}
    for ln in pdf_matches:
        pages.setdefault(ln["page"], []).append(ln)

    src = fitz.open(source_pdf_path)
    out = fitz.open()

    for page_num in sorted(pages.keys()):
        lines_on_page = pages[page_num]
        src_page      = src[page_num]
        page_rect     = src_page.rect

        # Remove spatial outliers with IQR
        if len(lines_on_page) >= 3:
            y_centers = sorted((ln["bbox"][1] + ln["bbox"][3]) / 2 for ln in lines_on_page)
            q1, q3    = y_centers[len(y_centers) // 4], y_centers[3 * len(y_centers) // 4]
            iqr       = q3 - q1
            lo, hi    = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            before    = len(lines_on_page)
            lines_on_page = [
                ln for ln in lines_on_page
                if lo <= (ln["bbox"][1] + ln["bbox"][3]) / 2 <= hi
            ]
            if len(lines_on_page) < before:
                print(f"   → Dropped {before - len(lines_on_page)} spatial outlier(s) on page {page_num + 1}")
        if not lines_on_page:
            continue

        # Union bbox of all matched lines → single region
        all_bboxes = [ln["bbox"] for ln in lines_on_page]
        x0 = max(min(b[0] for b in all_bboxes) - padding, page_rect.x0)
        y0 = max(min(b[1] for b in all_bboxes) - padding, page_rect.y0)
        x1 = min(max(b[2] for b in all_bboxes) + padding, page_rect.x1)
        y1 = min(max(b[3] for b in all_bboxes) + padding, page_rect.y1)

        clip_rect = fitz.Rect(x0, y0, x1, y1)
        w = x1 - x0
        h = y1 - y0

        # One output page sized exactly to the matched region
        new_page  = out.new_page(width=w, height=h)
        dest_rect = fitz.Rect(0, 0, w, h)
        new_page.show_pdf_page(dest_rect, src, page_num, clip=clip_rect)

        print(f"   → Page {page_num + 1}: extracted region ({w:.0f}×{h:.0f} pt) "
              f"with {len(lines_on_page)} matched block(s)")

    out.save(output_path, garbage=4, deflate=True)
    out.close()
    src.close()
    print(f"   → PDF saved: {output_path}")
    return output_path