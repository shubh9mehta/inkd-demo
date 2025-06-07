import os
import streamlit as st
from utils.pdf_generator import generate_pdf
from PIL import Image
import random
from utils.logo_fetcher import fetch_logo, save_logo
from utils.image_overlay import overlay_logo_on_product, pad_image_to_square
import tempfile

st.set_page_config(page_title="Get INK'D", layout="wide")

css_path = "assets/styles.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<div class='custom-header-bar'>
  <h1>ink’d</h1>
  <div class='subtitle'>AI-Powered Mockup Generator for Branded Merchandise</div>
</div>
""", unsafe_allow_html=True)

LOADING_MESSAGES = [
    "🎨 Generating your personalized swag...",
    "🪄 Summoning the AI design elves...",
    "🪾 Letting our robots iron your t-shirt mockup...",
    "🮢 Printing hats... and maybe a few dad jokes!",
    "🚀 Hold tight! Your brand's moment of glory is near.",
    "🤖 The AI is analyzing color vibes and logo power...",
    "🏱 Wrapping your virtual gift box...",
    "☕ Time for a coffee? We’ll be quick!"
]

# ---- Session State Setup ----
if "company_name" not in st.session_state:
    st.session_state.company_name = None
if "mockup_paths" not in st.session_state:
    st.session_state.mockup_paths = []

# ---- Main UI ----
with st.container():
    st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
    company_input = st.text_input(
        "Enter company website or name", key="input", label_visibility="visible"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    generate_clicked = st.button("Generate Mockups")
    st.markdown("</div>", unsafe_allow_html=True)

# Reset session if new company is entered
if company_input and company_input != st.session_state.company_name:
    st.session_state.company_name = company_input
    st.session_state.mockup_paths = []

if generate_clicked and company_input:
    with st.spinner(random.choice(LOADING_MESSAGES)):
        logo_bytes = fetch_logo(company_input)
        if not logo_bytes:
            st.error("⚠️ Could not fetch logo. Try a different site.")
        else:
            save_logo(logo_bytes, "output/logo_raw.png")

            product_dir = "assets/products"
            output_dir = "output/previews"
            os.makedirs(output_dir, exist_ok=True)

            product_paths = [
                os.path.join(product_dir, p)
                for p in os.listdir(product_dir)
                if p.lower().endswith((".png", ".jpg", ".jpeg"))
            ]

            st.session_state.mockup_paths = []
            for product_path in product_paths:
                filename = os.path.basename(product_path)
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_mockup.png")
                try:
                    overlay_logo_on_product(product_path, "output/logo_raw.png", output_path)
                    st.session_state.mockup_paths.append((filename, output_path))
                except Exception as e:
                    st.error(f"Error processing {filename}: {e}")

# ---- Upload Custom Image ----
with st.expander("Want to try your own product image? Click Here!"):
    st.markdown("💡 **Tip:** Upload a PNG file for best results. Our AI gets grumpy with Word docs! 😤")
    uploaded_file = st.file_uploader("Upload a custom product image (PNG preferred)", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        with st.spinner(random.choice(LOADING_MESSAGES)):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(uploaded_file.read())
                custom_input_path = tmp.name
            filename = os.path.basename(custom_input_path)
            output_path = f"output/previews/custom_{filename}"
            try:
                overlay_logo_on_product(custom_input_path, "output/logo_raw.png", output_path)
                st.session_state.mockup_paths.append((f"Custom - {filename}", output_path))
                st.success("🧵 Your custom product has joined the mockup parade!")
            except Exception as e:
                st.error(f"Failed to process custom image: {e}")

# ---- Display Mockups ----
if st.session_state.mockup_paths:
    st.markdown("<h2 class='stSubheader'>Your INK’D Merch</h2>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (filename, path) in enumerate(st.session_state.mockup_paths):
        with cols[i % 3]:
            try:
                img = Image.open(path)
                padded_img = pad_image_to_square(img, box_size=320, bgcolor=(255, 255, 255, 255))
                st.image(padded_img, caption=filename, use_container_width=False)
            except Exception as e:
                st.error(f"Display error: {e}")

    # ---- PDF Download with Multiselect ----
    mockup_image_options = {
        f"{i + 1}. {name}": path for i, (name, path) in enumerate(st.session_state.mockup_paths)
    }

    st.markdown("### 📂 Choose Mockups to Include in PDF")
    selected_keys = st.multiselect(
        " ",
        options=list(mockup_image_options.keys()),
        default=list(mockup_image_options.keys())
    )

    selected_paths = [mockup_image_options[k] for k in selected_keys]

    pdf_path = generate_pdf(selected_paths)
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download Selected Mockups as PDF",
                f,
                file_name="selected_mockups.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ---- Footer ----
st.markdown(
    "<div style='text-align:center; color:#9DB3C4; margin-top:2em;'>"
    "Built by Shubh Mehta for the Ink’d Recruitment challenge • &copy; 2025"
    "</div>",
    unsafe_allow_html=True
)