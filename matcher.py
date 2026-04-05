import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_arabic(text):
    text = re.sub(r'[\u0617-\u061A\u064B-\u065F]', '', text)
    text = re.sub(r'[أإآا]', 'ا', text)
    text = re.sub(r'[يى]', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    return text.strip()


def match_ocr_to_pdf_blocks(ocr_lines, pdf_blocks, threshold=0.15):
    if not pdf_blocks:
        return ocr_lines

    ocr_texts = [normalize_arabic(ln["raw_text"]) for ln in ocr_lines]
    pdf_texts  = [normalize_arabic(b["raw_text"])  for b in pdf_blocks]

    vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
    try:
        tfidf        = vectorizer.fit_transform(ocr_texts + pdf_texts)
        ocr_vecs     = tfidf[:len(ocr_texts)]
        pdf_vecs     = tfidf[len(ocr_texts):]
        similarities = cosine_similarity(ocr_vecs, pdf_vecs)
    except ValueError:
        return ocr_lines

    matched = []
    for i, ocr_line in enumerate(ocr_lines):
        best_idx   = np.argmax(similarities[i])
        best_score = similarities[i][best_idx]

        if best_score >= threshold:
            pdf_block = pdf_blocks[best_idx]
            matched.append({
                **ocr_line,
                "bbox":        pdf_block["bbox"],
                "page":        pdf_block["page"],
                "page_width":  pdf_block.get("page_width", 595),
                "page_height": pdf_block.get("page_height", 842),
                "match_score": round(float(best_score), 3)
            })
        else:
            matched.append({**ocr_line, "match_score": 0.0})

    return matched