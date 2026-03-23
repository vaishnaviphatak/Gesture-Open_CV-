import pytesseract
import re
import numpy as np
import cv2
from PIL import Image

# ICU Reference Ranges (Adults)
CRITICAL_RANGES = {
    "hemoglobin": {"min": 12.0, "max": 17.0, "unit": "g/dL", "alias": ["hgb", "hb"]},
    "wbc": {"min": 4000, "max": 11000, "unit": "/uL", "alias": ["white blood cell", "leukocyte count"]},
    "platelets": {"min": 150000, "max": 450000, "unit": "/uL", "alias": ["plt", "thrombocyte"]},
    "spo2": {"min": 95, "max": 100, "unit": "%", "alias": ["oxygen saturation", "sao2"]},
    "heart_rate": {"min": 60, "max": 100, "unit": "bpm", "alias": ["hr", "pulse"]},
    "sys_bp": {"min": 90, "max": 140, "unit": "mmHg", "alias": ["systolic"]},
    "dia_bp": {"min": 60, "max": 90, "unit": "mmHg", "alias": ["diastolic"]},
}

def analyze_image(image_path):
    """
    Directly OCRs an image and runs analysis.
    """
    try:
        # Load using PIL for better tesseract compatibility
        pil_img = Image.open(image_path)
        img = np.array(pil_img)
        
        # Pre-processing
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img

        # Denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Adaptive Thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        text = pytesseract.image_to_string(thresh).lower()
        return analyze_report(text)
    except Exception as e:
        print(f"Analysis Error: {e}")
        return []

def parse_blood_pressure(text):
    """
    Specifically looks for BP patterns like '120/80'.
    Returns sys, dia values if found.
    """
    # Regex for "BP 120/80" or just "120 / 80"
    bp_pattern = re.search(r'(?:bp|pressure)\s*[:\-]?\s*(\d{2,3})\s*/\s*(\d{2,3})', text)
    if bp_pattern:
        return int(bp_pattern.group(1)), int(bp_pattern.group(2))
    return None, None

def analyze_report(text):
    """
    Analyzes text for ICU parameters and validates against ranges.
    Returns a list of structured alert dictionaries.
    """
    alerts = []
    
    # Check BP first as it's often a combined string
    sys, dia = parse_blood_pressure(text)
    if sys and dia:
        _check_value("sys_bp", sys, alerts)
        _check_value("dia_bp", dia, alerts)

    for param, info in CRITICAL_RANGES.items():
        if param in ["sys_bp", "dia_bp"]: continue # Handled above

        # Create regex pattern for aliases
        aliases = "|".join([param] + info["alias"])
        pattern = re.search(rf"({aliases})\s*[:\-]?\s*(\d+(\.\d+)?)", text)
        
        if pattern:
            try:
                value = float(pattern.group(2))
                _check_value(param, value, alerts)
            except ValueError:
                continue
                
    return alerts

def _check_value(param_key, value, alerts_list):
    """
    Helper to validate value and append to alerts.
    """
    info = CRITICAL_RANGES[param_key]
    status = "NORMAL"
    
    if value < info["min"]:
        status = "LOW"
    elif value > info["max"]:
        status = "HIGH"
        
    if status != "NORMAL":
        alerts_list.append({
            "param": param_key.upper().replace("_", " "),
            "value": value,
            "unit": info["unit"],
            "status": status,
            "range": f"{info['min']}-{info['max']}"
        })
