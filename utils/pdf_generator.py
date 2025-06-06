from PIL import Image
import os

def generate_pdf(image_paths, pdf_path="output/mockups.pdf"):
    images = [Image.open(p).convert("RGB") for p in image_paths if os.path.exists(p)]
    if images:
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        return pdf_path
    return None
