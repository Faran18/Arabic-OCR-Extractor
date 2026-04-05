import sys
import os
from ocr_engine  import extract_from_image
from pdf_handler import pdf_to_images, extract_pdf_blocks
from matcher     import match_ocr_to_pdf_blocks
from formatter   import export_to_html, export_to_text, export_summary, export_to_pdf

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}


def process(input_path, ref_pdf_path=None):
    if not os.path.exists(input_path):
        print(f"\n❌ File not found: {input_path}\n")
        return

    ext = os.path.splitext(input_path)[1].lower()

    if ext == '.pdf' and ref_pdf_path is None:
        print("\n📄 PDF detected...\n")
        pdf_blocks  = extract_pdf_blocks(input_path)
        print("\n   Running EasyOCR on rendered pages...\n")
        image_paths = pdf_to_images(input_path)
        ocr_lines   = []
        for img_path in image_paths:
            ocr_lines.extend(extract_from_image(img_path))
        source_pdf = input_path

    elif ext in IMAGE_EXTS and ref_pdf_path is not None:
        if not os.path.exists(ref_pdf_path):
            print(f"\n❌ Reference PDF not found: {ref_pdf_path}\n")
            return
        if os.path.splitext(ref_pdf_path)[1].lower() != '.pdf':
            print(f"\n❌ Second argument must be a PDF file: {ref_pdf_path}\n")
            return
        print("\n📷 Image + PDF mode detected...\n")
        print("   Step 1 — OCR on image\n")
        ocr_lines  = extract_from_image(input_path)
        print(f"\n   Step 2 — Extracting text blocks from reference PDF\n")
        pdf_blocks = extract_pdf_blocks(ref_pdf_path)
        source_pdf = ref_pdf_path

    elif ext in IMAGE_EXTS:
        print("\n📷 Image detected — running OCR...\n")
        ocr_lines  = extract_from_image(input_path)
        pdf_blocks = []
        source_pdf = None

    else:
        print(f"\n❌ Unsupported input: {input_path}")
        print("   Supported: .jpg .jpeg .png .bmp .tiff .pdf\n")
        return

    ocr_lines = [
        ln for ln in ocr_lines
        if len(ln.get("raw_text", "").strip()) >= 3 and ln.get("confidence", 0) >= 0.35
    ]

    print(f"\n✅ OCR complete — {len(ocr_lines)} lines extracted")
    print("\n🔗 Matching lines to PDF layout...\n")
    matched = match_ocr_to_pdf_blocks(ocr_lines, pdf_blocks)

    n_matched = sum(1 for ln in matched if ln.get("match_score", 0) > 0)
    print(f"   → {n_matched}/{len(matched)} lines matched to PDF blocks")

    print("\n💾 Saving outputs...\n")
    export_to_html(matched)
    export_to_text(matched)
    export_summary(matched)

    if source_pdf:
        export_to_pdf(matched, source_pdf)

    print("\n✅ Done! output/ folder contains:")
    print("   result.html   ← RTL layout in browser")
    print("   result.txt    ← plain Arabic text")
    print("   summary.txt   ← per-line confidence + match scores")
    if source_pdf:
        print("   result.pdf    ← matched PDF regions with exact formatting")
    print()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        process(sys.argv[1])
    elif len(sys.argv) == 3:
        process(sys.argv[1], sys.argv[2])
    else:
        print("\nUsage:")
        print("   python main.py <document.pdf>")
        print("   python main.py <scan_image.jpg> <reference.pdf>\n")
        print("Examples:")
        print("   python main.py example.pdf")
        print("   python main.py input/arabic_scan.jpg example.pdf\n")