import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
from rembg import remove
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

def resolve_company_to_domain_gpt(user_input):
    """
    Use GPT to resolve any company-related input into its official website domain.
    """
    prompt = (
        "You are an AI assistant that returns only the official website domain (e.g., 'netflix.com') "
        "for real-world companies or brands based on the user's input.\n\n"
        "Instructions:\n"
        "- If the input is already a valid domain or URL, return the domain part only (e.g., 'apple.com').\n"
        "- If the input is a company name, return the official website domain.\n"
        "- If the input has a typo (e.g., 'gogl' instead of 'Google'), infer the correct company and return its domain.\n"
        "- If the input is a product name (e.g., 'iPhone'), return the domain of the company that owns it (e.g., 'apple.com').\n"
        "- If the input is a **descriptive phrase** (e.g., 'fun, bold merch brand'), return the domain of a real company that matches that description.\n"
        "- If you cannot determine the company confidently, default to 'inkdstores.com'.\n\n"
        "IMPORTANT:\n"
        "- ALWAYS return ONLY the bare domain name (e.g., 'nike.com') — no explanation, no extra text, no http/https, and no subdomains.\n\n"
        f"Input: {user_input}\n"
        "Domain:"
    )

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You return only the official domain name of the company, and nothing else."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=25,
        temperature=0
    )

    text = resp.choices[0].message.content.strip()
    # Sanity: only domain, no protocol/extra text
    text = text.replace("https://", "").replace("http://", "").split("/")[0]
    return text

CLEARBIT_API = "https://logo.clearbit.com/"

def get_domain(url_or_name):
    # Use GPT to resolve company name to domain if needed
    domain = resolve_company_to_domain_gpt(url_or_name)
    return domain

def fetch_logo(company_url_or_name):
    domain = get_domain(company_url_or_name)
    # 1. Clearbit API
    try:
        cb_url = f"{CLEARBIT_API}{domain}"
        cb_res = requests.get(cb_url, timeout=3)
        if cb_res.status_code == 200 and cb_res.headers.get("Content-Type", "").startswith("image"):
            print("[LOGO] Found via Clearbit.")
            return cb_res.content
    except Exception as e:
        print("Clearbit error:", e)

    homepage = f"https://{domain}"
    try:
        resp = requests.get(homepage, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 2. Meta/link icons
        for rel in ['icon', 'shortcut icon', 'apple-touch-icon']:
            icon = soup.find("link", rel=lambda x: x and rel in x.lower())
            if icon and icon.get("href"):
                logo_url = urljoin(homepage, icon['href'])
                r = requests.get(logo_url, timeout=3)
                if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                    print(f"[LOGO] Found via <link rel='{rel}'>.")
                    return r.content

        # 3. Open Graph
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            og_url = urljoin(homepage, og_image["content"])
            r = requests.get(og_url, timeout=3)
            if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                print("[LOGO] Found via og:image.")
                return r.content

        # 4. <img> with 'logo'
        for img in soup.find_all("img"):
            attrs = (img.get("alt", "") + " " + str(img.get("class", "")) + " " + img.get("src", "")).lower()
            if "logo" in attrs:
                src = img.get("src")
                if src:
                    logo_url = urljoin(homepage, src)
                    r = requests.get(logo_url, timeout=3)
                    if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                        print("[LOGO] Found via <img> with 'logo'.")
                        return r.content

        # 5. Favicon fallback
        favicon_url = urljoin(homepage, "favicon.ico")
        r = requests.get(favicon_url, timeout=3)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            print("[LOGO] Found via favicon.")
            return r.content

    except Exception as e:
        print("Logo fetch error:", e)

    print("[LOGO] Not found.")
    return None

def add_outline(image, outline_width=2, outline_color=(50, 50, 50, 255)):
    alpha = image.split()[-1]
    mask = ImageOps.expand(alpha, border=outline_width, fill=0)
    mask = mask.filter(ImageFilter.MaxFilter(outline_width * 2 + 1))
    outline = Image.new("RGBA", mask.size, outline_color)
    base = Image.new("RGBA", mask.size, (0,0,0,0))
    base.paste(outline, mask=mask)
    base.paste(image, (outline_width, outline_width), image)
    return base

def save_logo(content, output_path="output/logo_raw.png"):
    try:
        img = Image.open(BytesIO(content)).convert("RGBA")
        img_nobg = remove(img)
        img_with_outline = add_outline(img_nobg)
        img_with_outline.save(output_path)
        print(f"Logo saved to {output_path} (bg removed, outline added)")
    except Exception as e:
        print("Failed to save logo:", e)
