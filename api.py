import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ocr_engine  import extract_from_image
from pdf_handler import pdf_to_images, extract_pdf_blocks
from matcher     import match_ocr_to_pdf_blocks
from formatter   import export_to_html, export_to_text, export_summary, export_to_pdf

app = FastAPI(title="Arabic OCR Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def run_pipeline(input_path: Path, ref_pdf_path: Path = None):
    ext = input_path.suffix.lower()

    if ext == ".pdf" and ref_pdf_path is None:
        pdf_blocks  = extract_pdf_blocks(str(input_path))
        image_paths = pdf_to_images(str(input_path))
        ocr_lines   = []
        for img in image_paths:
            ocr_lines.extend(extract_from_image(img))
        source_pdf = str(input_path)

    elif ext in IMAGE_EXTS and ref_pdf_path is not None:
        ocr_lines  = extract_from_image(str(input_path))
        pdf_blocks = extract_pdf_blocks(str(ref_pdf_path))
        source_pdf = str(ref_pdf_path)

    elif ext in IMAGE_EXTS:
        ocr_lines  = extract_from_image(str(input_path))
        pdf_blocks = []
        source_pdf = None

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    ocr_lines = [
        ln for ln in ocr_lines
        if len(ln.get("raw_text", "").strip()) >= 3 and ln.get("confidence", 0) >= 0.35
    ]

    matched = match_ocr_to_pdf_blocks(ocr_lines, pdf_blocks)

    export_to_html(matched)
    export_to_text(matched)
    export_summary(matched)
    if source_pdf:
        export_to_pdf(matched, source_pdf)

    n_matched = sum(1 for ln in matched if ln.get("match_score", 0) > 0)
    return {
        "ocr_lines":  len(ocr_lines),
        "matched":    n_matched,
        "has_pdf":    source_pdf is not None,
    }


@app.post("/process")
async def process(
    input_file: UploadFile = File(...),
    reference_pdf: UploadFile = File(None),
):
    uid        = uuid.uuid4().hex
    input_ext  = Path(input_file.filename).suffix.lower()
    input_path = UPLOAD_DIR / f"{uid}_input{input_ext}"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(input_file.file, f)

    ref_path = None
    if reference_pdf and reference_pdf.filename:
        ref_path = UPLOAD_DIR / f"{uid}_ref.pdf"
        with open(ref_path, "wb") as f:
            shutil.copyfileobj(reference_pdf.file, f)

    try:
        stats = run_pipeline(input_path, ref_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({
        "status":     "ok",
        "ocr_lines":  stats["ocr_lines"],
        "matched":    stats["matched"],
        "outputs": {
            "html":    "/download/result.html",
            "txt":     "/download/result.txt",
            "summary": "/download/summary.txt",
            **({"pdf": "/download/result.pdf"} if stats["has_pdf"] else {}),
        }
    })


@app.get("/download/{filename}")
async def download(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


# Serve the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")