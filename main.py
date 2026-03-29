import sys
import os
from ocr_engine  import extract_from_image
from pdf_handler import pdf_to_images, extract_pdf_blocks
from matcher     import match_ocr_to_pdf_blocks
from formatter   import export_to_html, export_to_text, export_summary


def process(input_path):
    if not os.path.exists(input_path):
        print(f"\n❌ File not found: {input_path}\n")
        return

    ext = os.path.splitext(input_path)[1].lower()

    
    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print("\n📷 Image detected — running OCR...\n")
        ocr_lines  = extract_from_image(input_path)
        pdf_blocks = []

   
    elif ext == '.pdf':
        print("\n📄 PDF detected...\n")

       
        pdf_blocks = extract_pdf_blocks(input_path)

        
        print("\n   Running EasyOCR on rendered pages...\n")
        image_paths = pdf_to_images(input_path)
        ocr_lines   = []
        for img_path in image_paths:
            ocr_lines.extend(extract_from_image(img_path))

    else:
        print(f"\n❌ Unsupported format: {ext}")
        print("   Supported types: .jpg .jpeg .png .bmp .tiff .pdf\n")
        return

    print(f"\n✅ OCR complete — {len(ocr_lines)} lines extracted")

    
    print("\n🔗 Matching lines to layout...\n")
    matched = match_ocr_to_pdf_blocks(ocr_lines, pdf_blocks)

    
    print("\n💾 Saving outputs...\n")
    export_to_html(matched)
    export_to_text(matched)
    export_summary(matched)

    print("\n✅ All done! Your output/ folder now contains:")
    print("   result.html   ← open in browser (RTL layout preserved)")
    print("   result.txt    ← plain Arabic text")
    print("   summary.txt   ← confidence scores per line (debug)\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage:   python main.py <your_file>")
        print("Examples:")
        print("   python main.py input/arabic_scan.jpg")
        print("   python main.py input/document.pdf\n")
    else:
        process(sys.argv[1])