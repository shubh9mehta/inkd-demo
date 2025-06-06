import os
import streamlit as st
from utils.pdf_generator import generate_pdf
from PIL import Image
import random  # <-- Added for random loading message

# 1. Set Streamlit page config (must be first Streamlit command)
st.set_page_config(page_title="Get INK'D", layout="wide")

# 2. Load custom CSS after set_page_config
css_path = "assets/styles.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 3. Custom Ink'd-style header (replace st.title)
st.markdown("""
<div class='custom-header-bar'>
  <h1>ink’d</h1>
  <div class='subtitle'>AI-Powered Mockup Generator for Branded Merchandise</div>
</div>
""", unsafe_allow_html=True)

from utils.logo_fetcher import fetch_logo, save_logo
from utils.image_overlay import overlay_logo_on_product, pad_image_to_square  # import the pad function

# ---- Fun loading messages ----
LOADING_MESSAGES = [
    "🎨 Generating your personalized swag...",
    "🪄 Summoning the AI design elves...",
    "🦾 Letting our robots iron your t-shirt mockup...",
    "🧢 Printing hats... and maybe a few dad jokes!",
    "🚀 Hold tight! Your brand's moment of glory is near.",
    "🤖 The AI is analyzing color vibes and logo power...",
    "🎁 Wrapping your virtual gift box...",
    "☕ Time for a coffee? We’ll be quick!"
]

# 4. Main UI
company_input = st.text_input("Enter company website or name")

if st.button("Generate Mockups") and company_input:
    with st.spinner(random.choice(LOADING_MESSAGES)):   # <--- Here!
        logo_bytes = fetch_logo(company_input)
        if not logo_bytes:
            st.error("⚠️ Could not fetch logo. Try a different site.")
        else:
            save_logo(logo_bytes, "output/logo_raw.png")
            st.success("🎉 Your logo is INK’D! Let’s see it on some swag…")

            # Process all products dynamically
            st.markdown("<h2 class='stSubheader'>Your INK’D Merch</h2>", unsafe_allow_html=True)
            product_dir = "assets/products"
            output_dir = "output/previews"
            os.makedirs(output_dir, exist_ok=True)

            # Find all product images (png, jpg, jpeg)
            product_paths = [
                os.path.join(product_dir, p)
                for p in os.listdir(product_dir)
                if p.lower().endswith((".png", ".jpg", ".jpeg"))
            ]

            cols = st.columns(3)
            i = 0

            for product_path in product_paths:
                filename = os.path.basename(product_path)
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_mockup.png")

                try:
                    overlay_logo_on_product(product_path, "output/logo_raw.png", output_path)
                    # --- Containerize for grid layout using pad_image_to_square ---
                    with cols[i % 3]:
                        try:
                            img = Image.open(output_path)
                            padded_img = pad_image_to_square(img, box_size=320, bgcolor=(255,255,255,255))
                            st.image(padded_img, caption=filename, use_container_width=False)
                        except Exception as e:
                            st.error(f"Error displaying image: {e}")
                except Exception as e:
                    with cols[i % 3]:
                        st.error(f"Failed to process {filename}: {e}")
                i += 1

            # ---- PDF Export Button ----
            mockup_image_paths = [
                os.path.join(output_dir, f"{os.path.splitext(os.path.basename(p))[0]}_mockup.png")
                for p in product_paths
            ]
            pdf_path = generate_pdf(mockup_image_paths)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download All INK'D Merch as PDF",
                        f,
                        file_name="mockups.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

# Optionally, add a footer (brand-like)
st.markdown(
    "<div style='text-align:center; color:#9DB3C4; margin-top:2em;'>"
    "Built by Shubh Mehta for the Ink’d Recruitment challenge • &copy; 2025"
    "</div>",
    unsafe_allow_html=True
)