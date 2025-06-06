from PIL import Image, ImageOps, ImageDraw, ImageChops, ImageFilter
import os
import numpy as np
from utils.product_inspector_sam import get_sam_bounding_box, get_sam_bounding_box_and_angle
from utils.logo_size_gpt import get_logo_scale_percentages

# --- UTIL: Pad/crop to square container for nice Streamlit grid ---
def pad_image_to_square(image, box_size=320, bgcolor=(255,255,255,255)):
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    image.thumbnail((box_size, box_size), Image.Resampling.LANCZOS)
    w, h = image.size
    padded = Image.new("RGBA", (box_size, box_size), bgcolor)
    padded.paste(image, ((box_size - w) // 2, (box_size - h) // 2), image)
    return padded

def is_mostly_white(img, threshold=240, frac=0.75):
    arr = np.array(img.convert("RGB"))
    mask = np.all(arr > threshold, axis=-1)
    return mask.mean() > frac

def dominant_color(img):
    """Get dominant color of an RGBA or RGB image as (r,g,b) tuple."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img).reshape(-1, 3)
    arr = arr[~np.all(arr == 255, axis=1)]  # Remove pure white BG
    if len(arr) == 0:
        return (180,180,180)
    colors, counts = np.unique(arr, axis=0, return_counts=True)
    return tuple(colors[np.argmax(counts)])

def luminance(c):
    r,g,b = c
    return 0.299*r + 0.587*g + 0.114*b

def pick_border_color(logo_dom, prod_dom):
    """Choose a border color that stands out against both logo and product region."""
    # If both are light, pick dark. If both dark, pick light.
    if luminance(logo_dom) > 180 and luminance(prod_dom) > 180:
        return (40, 56, 80, 255)   # dark navy
    if luminance(logo_dom) < 70 and luminance(prod_dom) < 70:
        return (255,255,255,255)
    # Else, use high-contrast gray
    return (60, 60, 60, 255)

# --- Mask-based outline for logos ---
def mask_outline(mask, outline_width):
    """Dilate the alpha mask to create an outline mask."""
    if mask.mode != "L":
        mask = mask.convert("L")
    expanded = mask.filter(ImageFilter.MaxFilter(outline_width * 2 + 1))
    outline_mask = ImageChops.difference(expanded, mask)
    return outline_mask

def add_logo_border_auto(logo, product_region, border=2):
    """
    Adds a mask-following outline of 'border' px around the logo's nontransparent region,
    using a smart color matched to the logo/product.
    """
    logo_dom = dominant_color(logo)
    prod_dom = dominant_color(product_region)
    border_color = pick_border_color(logo_dom, prod_dom)

    alpha = logo.split()[-1]
    outline_mask = mask_outline(alpha, border)
    outline = Image.new("RGBA", logo.size, (0,0,0,0))
    outline_draw = ImageDraw.Draw(outline)
    outline_draw.bitmap((0,0), outline_mask, fill=border_color)
    # Composite: put outline under original logo (centered, same size)
    bordered = Image.alpha_composite(outline, logo)
    return bordered

def overlay_logo_on_product(product_path, logo_path, output_path, pad_to_square=True, box_size=320):
    product = Image.open(product_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")
    product_name = os.path.basename(product_path).split('.')[0].lower()

    # For bottles, use angle-aware placement
    if "bottle" in product_name:
        box, angle = get_sam_bounding_box_and_angle(product_path)
    else:
        box = get_sam_bounding_box(product_path)
        angle = 0.0

    box_w, box_h = box[2] - box[0], box[3] - box[1]
    logo_orig_size = logo.size
    image_size = product.size

    # Get GPT-recommended scale
    (width_pct, height_pct), comment = get_logo_scale_percentages(
        product_name, image_size, box, logo_orig_size
    )

    max_w = int(box_w * width_pct)
    max_h = int(box_h * height_pct)
    aspect = logo_orig_size[0] / logo_orig_size[1]
    if max_w / aspect <= max_h:
        logo_w = max_w
        logo_h = int(max_w / aspect)
    else:
        logo_h = max_h
        logo_w = int(max_h * aspect)

    logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    # White-on-white: add smart border (now mask-following)
    product_crop = product.crop((box[0], box[1], box[2], box[3])).resize((logo_w, logo_h))
    if is_mostly_white(logo) and is_mostly_white(product_crop):
        logo = add_logo_border_auto(logo, product_crop, border=2)

    # Angle logic for bottles
    if abs(angle) > 2:
        logo = logo.rotate(-angle, expand=True, resample=Image.BICUBIC)

    # Chest placement for t-shirt
    if "shirt" in product_name or "tshirt" in product_name:
        chest_y = int(box[1] + box_h * 0.35 - logo.height // 2)
        y_offset = max(box[1], min(chest_y, box[3] - logo.height))
        x_offset = box[0] + (box_w - logo.width) // 2
    else:
        x_offset = box[0] + (box_w - logo.width) // 2
        y_offset = box[1] + (box_h - logo.height) // 2

    product.paste(logo, (x_offset, y_offset), logo)

    # -- Containerize for grid layout if requested
    if pad_to_square:
        final_img = pad_image_to_square(product, box_size=box_size, bgcolor=(255,255,255,255))
        final_img.save(output_path)
    else:
        product.save(output_path)
