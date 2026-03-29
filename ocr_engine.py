import cv2
import numpy as np
import easyocr
import arabic_reshaper
from bidi.algorithm import get_display
import os

reader = easyocr.Reader(['ar'], gpu=False)

def fix_arabic(text):
    return text

def is_image_clean(image_path):
    img  = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    std  = np.std(img)     
    mean = np.mean(img)     
    
    
    return mean > 150 and std > 30


def clean_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not open: {image_path}")

    # If image is already clean, skip all preprocessing
    if is_image_clean(image_path):
        print("   → Image is already clean — skipping preprocessing")
        return image_path   # use original directly

    print("   → Image needs cleaning — applying fixes...")
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    
    _, binary = cv2.threshold(
        denoised, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    cleaned_path = "input/preprocessed.jpg"
    cv2.imwrite(cleaned_path, binary)
    print(f"   → Cleaned image saved: {cleaned_path}")
    return cleaned_path


def extract_from_image(image_path):
    print(f"   → Running OCR on: {image_path}")
    ready = clean_image(image_path)

    img = cv2.imread(ready)
    scale = 2.5
    upscaled = cv2.resize(
        img, 
        (int(img.shape[1] * scale), int(img.shape[0] * scale)),
        interpolation=cv2.INTER_CUBIC
    )

    lab = cv2.cvtColor(upscaled, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    boosted = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    
    raw = reader.readtext(
        boosted,
        detail=1,
        paragraph=False,      
        width_ths=0.3,        
        contrast_ths=0.05,
        text_threshold=0.3,
        low_text=0.3
    )

    valid_boxes = []
    for (corners, text, confidence) in raw:
        if not text.strip() or confidence < 0.20:  
            continue
            
        
        y_center = sum([pt[1] for pt in corners]) / 4
        x_center = sum([pt[0] for pt in corners]) / 4
        height = max([pt[1] for pt in corners]) - min([pt[1] for pt in corners])
        
        valid_boxes.append({
            "text": text,
            "y_center": y_center,
            "x_center": x_center,
            "corners": corners,
            "confidence": confidence,
            "height": height
        })

    
    valid_boxes.sort(key=lambda box: box["y_center"])

    
    visual_lines = []
    current_line = []

    for box in valid_boxes:
        if not current_line:
            current_line.append(box)
        else:
            
            avg_y = sum([b["y_center"] for b in current_line]) / len(current_line)
            avg_h = sum([b["height"] for b in current_line]) / len(current_line)
            
            
            if abs(box["y_center"] - avg_y) < (avg_h * 0.6):
                current_line.append(box)
            else:
                
                visual_lines.append(current_line)
                current_line = [box]
    
    if current_line:
        visual_lines.append(current_line)

    # Sort each line Right-to-Left and format for HTML
    final_output = []
    for line_group in visual_lines:
        # Sort Right-to-Left (Highest X to Lowest X)
        line_group.sort(key=lambda box: box["x_center"], reverse=True)
        
        # Join words together with spaces
        line_text = " ".join([box["text"] for box in line_group])
        
        # Calculate full bounding box for the line
        all_x = [pt[0] for b in line_group for pt in b["corners"]]
        all_y = [pt[1] for b in line_group for pt in b["corners"]]
        avg_conf = sum([b["confidence"] for b in line_group]) / len(line_group)
        
        final_output.append({
            "text":       fix_arabic(line_text),
            "raw_text":   line_text,
            "bbox":       [min(all_x), min(all_y), max(all_x), max(all_y)],
            "confidence": round(avg_conf, 3),
            "page":       0
        })

    print(f"   → Grouped into {len(final_output)} physical lines")
    return final_output