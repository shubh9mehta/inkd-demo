import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

def get_logo_scale_percentages(product_name, image_size, box_coords, logo_size):
    image_width, image_height = image_size
    logo_width, logo_height = logo_size
    x1, y1, x2, y2 = box_coords

    prompt = f"""
You are a visual design AI assistant helping optimize logo placement on promotional products.
The product is: {product_name}
Image size: {image_width}x{image_height}
Printable area (detected box): ({x1}, {y1}, {x2}, {y2})
Logo original size: {logo_width}x{logo_height}

Key requirements:
- Recommend LARGE and BOLD logo sizes that make a strong visual impact
- Logo should be prominently visible and make a statement
- For t-shirts: logo should take up 60-80% of the chest area
- For bottles: logo should take up 50-70% of the printable area
- For mugs: logo should take up 60-75% of the printable area
- For diaries/notebooks: logo should take up 70-90% of the cover
- For other products: logo should take up 50-70% of the printable area
- Preserve the logo's original aspect ratio
- Never make logos too small - err on the side of larger sizes

Output only valid JSON with the following format:
{{
  "width_pct": 0.8,
  "height_pct": 0.8,
  "comment": "Large, impactful logo sized at 80% for maximum visibility"
}}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a visual branding AI."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=200
    )

    content = response.choices[0].message.content

    # Safer extraction for robustness
    try:
        json_str = re.search(r'{.*}', content, re.DOTALL).group(0)
        data = json.loads(json_str)
        return (float(data["width_pct"]), float(data["height_pct"])), data["comment"]
    except Exception as e:
        print("❌ Error parsing GPT output:", content)
        raise e