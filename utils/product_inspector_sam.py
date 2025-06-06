import os
import pickle
import cv2
import numpy as np
import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

sam_checkpoint = "models/sam_vit_b_01ec64.pth"
sam = sam_model_registry["vit_b"](checkpoint=sam_checkpoint)
sam.to("cpu")

mask_generator = SamAutomaticMaskGenerator(
    model=sam,
    points_per_side=16,
    pred_iou_thresh=0.88,
    stability_score_thresh=0.95,
    min_mask_region_area=1000,
)

def clamp_box_within(image_shape, box, max_ratio=0.35):
    height, width = image_shape[:2]
    x1, y1, x2, y2 = box
    box_w = min(x2 - x1, int(width * max_ratio))
    box_h = min(y2 - y1, int(height * max_ratio))

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    x1 = max(0, cx - box_w // 2)
    y1 = max(0, cy - box_h // 2)
    x2 = min(width, x1 + box_w)
    y2 = min(height, y1 + box_h)
    return (x1, y1, x2, y2)

def get_sam_cache_path(image_path):
    cache_dir = "cache/sam"
    os.makedirs(cache_dir, exist_ok=True)
    fname = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(cache_dir, f"{fname}.pkl")

def get_sam_bounding_box_and_angle(image_path):
    cache_path = get_sam_cache_path(image_path)
    # Try to load cache first
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            result = pickle.load(f)
            # box, angle, mask are stored
            return result['box'], result['angle']
    
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image at {image_path}")

    masks = mask_generator.generate(image)
    masks = sorted(masks, key=lambda x: x['area'], reverse=True)
    height, width = image.shape[:2]
    img_area = height * width

    for mask in masks:
        seg = mask['segmentation'].astype(np.uint8) * 255
        x, y, w, h = cv2.boundingRect(seg)
        area = w * h
        if area > img_area * 0.6:
            continue

        # Orientation by moments
        moments = cv2.moments(seg)
        angle = 0.0
        if abs(moments["mu20"] - moments["mu02"]) > 1e-2:
            angle = 0.5 * np.arctan2(2 * moments["mu11"], moments["mu20"] - moments["mu02"])
            angle = np.degrees(angle) + 90

        box = (x, y, x + w, y + h)
        box = clamp_box_within(image.shape, box)
        # Save all info
        result = {
            "box": box,
            "angle": angle,
            "mask": seg,  # Save the mask if needed for future features
        }
        with open(cache_path, "wb") as f:
            pickle.dump(result, f)
        return box, angle

    # Fallback (no mask found)
    box_size = int(min(width, height) * 0.3)
    x1 = (width - box_size) // 2
    y1 = (height - box_size) // 2
    fallback = {"box": (x1, y1, x1 + box_size, y1 + box_size), "angle": 0.0, "mask": None}
    with open(cache_path, "wb") as f:
        pickle.dump(fallback, f)
    return fallback["box"], fallback["angle"]

def get_sam_bounding_box(image_path):
    box, _ = get_sam_bounding_box_and_angle(image_path)
    return box
