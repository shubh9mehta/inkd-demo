import cv2
import numpy as np

def get_smart_logo_box(image_path, max_logo_ratio=0.3):
    # Load the image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not load image at {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Blur slightly to remove noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use adaptive threshold to detect large light areas (flat surfaces)
    thresh = cv2.adaptiveThreshold(blurred, 255,
                                   cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    height, width = gray.shape
    logo_area_limit = width * height * max_logo_ratio

    best_box = None
    best_score = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        # Filter small/noisy regions and too big regions
        if 10000 < area < logo_area_limit:
            score = area - abs(w - h)  # Prefer near-square flat zones
            if score > best_score:
                best_score = score
                best_box = (x, y, x + w, y + h)

    # Fallback to center box if no good region found
    if best_box is None:
        box_size = int(min(width, height) * 0.25)
        x = (width - box_size) // 2
        y = (height - box_size) // 2
        best_box = (x, y, x + box_size, y + box_size)

    return best_box
