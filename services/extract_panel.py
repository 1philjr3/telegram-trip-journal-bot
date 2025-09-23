from dataclasses import dataclass
import os
import io
import numpy as np
import cv2
import pytesseract
from PIL import Image


@dataclass
class PanelReading:
    odometer_km: int | None
    fuel_bars: int | None
    confidence: float


def _get_env_tuple(name: str, default: str) -> tuple[int, int, int, int]:
    val = os.getenv(name, default)
    try:
        x, y, w, h = [int(v.strip()) for v in val.split(',')]
        return x, y, w, h
    except Exception:
        x, y, w, h = [int(v.strip()) for v in default.split(',')]
        return x, y, w, h


def _prep_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return gray


def _ocr_digits(img: np.ndarray) -> tuple[int | None, float]:
    gray = _prep_gray(img)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    config = f"--psm {os.getenv('OCR_PSM','7')} -c tessedit_char_whitelist=0123456789"
    lang = os.getenv('OCR_LANG', 'eng')
    if os.getenv('TESSERACT_CMD'):
        pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD')

    pil_img = Image.fromarray(th)
    text = pytesseract.image_to_string(pil_img, config=config, lang=lang)
    digits = ''.join(ch for ch in text if ch.isdigit())
    if len(digits) < 3:
        return None, 0.2
    try:
        value = int(digits)
        conf = min(1.0, 0.5 + 0.05 * len(digits))
        return value, conf
    except Exception:
        return None, 0.2


def _count_fuel_bars(img: np.ndarray, bars: int, thresh_ratio: float) -> tuple[int | None, float]:
    gray = _prep_gray(img)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    h, w = th.shape
    bin_h = h // max(bars, 1)
    on = 0
    margins = []
    for i in range(bars):
        y0 = i * bin_h
        y1 = h if i == bars - 1 else (i + 1) * bin_h
        roi = th[y0:y1, :]
        light_ratio = (roi > 200).mean() if roi.size else 0.0
        margins.append(abs(light_ratio - thresh_ratio))
        if light_ratio > thresh_ratio:
            on += 1
    if on < 0 or on > bars:
        return None, 0.2
    conf = min(1.0, 0.5 + float(np.mean(margins)))
    return on, conf


def extract_from_image(image_bytes: bytes) -> PanelReading:
    FUEL_BARS = int(os.getenv('FUEL_BARS', '8'))
    THRESH_FUEL = float(os.getenv('THRESH_FUEL', '0.4'))

    # Задаем ROI по env (по умолчанию нужно будет откалибровать под вашу приборку)
    ROI_ODO = _get_env_tuple('ROI_ODO', os.getenv('ROI_ODO_DEFAULT', '100,100,300,120'))
    ROI_FUEL = _get_env_tuple('ROI_FUEL', os.getenv('ROI_FUEL_DEFAULT', '500,100,60,400'))

    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return PanelReading(None, None, 0.0)

    h, w = image.shape[:2]
    x, y, rw, rh = ROI_ODO
    x2, y2, rw2, rh2 = ROI_FUEL
    x = max(0, min(w - 1, x)); y = max(0, min(h - 1, y))
    x2 = max(0, min(w - 1, x2)); y2 = max(0, min(h - 1, y2))
    odo_roi = image[y:y+rh, x:x+rw]
    fuel_roi = image[y2:y2+rh2, x2:x2+rw2]

    odo_val, odo_conf = _ocr_digits(odo_roi) if odo_roi.size else (None, 0.0)
    bars_val, bars_conf = _count_fuel_bars(fuel_roi, FUEL_BARS, THRESH_FUEL) if fuel_roi.size else (None, 0.0)

    conf = float(np.mean([c for c in [odo_conf, bars_conf] if c is not None])) if (odo_conf or bars_conf) else 0.0
    return PanelReading(odo_val, bars_val, conf)

