import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re
import base64
import os

# --- HELPER FUNCTIONS ---
def extract_app_id(play_store_url):
    match = re.search(r'id=([^&]+)', play_store_url)
    return match.group(1) if match else None

def fetch_app_icon(play_store_url):
    try:
        app_id = extract_app_id(play_store_url)
        if not app_id:
            st.warning("Invalid Play Store URL. Please provide a valid URL.")
            return None
        response = requests.get(f'https://play.google.com/store/apps/details?id={app_id}')
        icon_match = re.search(r'https://play-lh\.googleusercontent\.com/[^"]+', response.text)
        if icon_match:
            icon_url = re.sub(r'=s\d+', '=s512', icon_match.group(0))
            icon_response = requests.get(icon_url)
            return Image.open(BytesIO(icon_response.content))
    except Exception as e:
        st.error(f"Failed to fetch app icon: {e}")
        return None

def create_rounded_rectangle_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def load_badge_from_file(file_path, width=540):
    try:
        # First try to open as PNG (if you've pre-converted the SVGs)
        if file_path.endswith('.png'):
            return Image.open(file_path).resize((width, int(width * (3/14))), Image.Resampling.LANCZOS)

        # If you want to keep using SVGs, you'll need to convert them to PNG first
        # For now, we'll fall back to downloading the badges
        if "App_Store" in file_path:
            url = 'https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us'
        else:
            url = 'https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png'

        response = requests.get(url, timeout=10)
        badge = Image.open(BytesIO(response.content))
        aspect_ratio = badge.height / badge.width
        return badge.resize((width, int(width * aspect_ratio)), Image.Resampling.LANCZOS)
    except Exception as e:
        st.error(f"Failed to load badge: {e}")
        return None

def generate_ctv_tile(app_name, play_store_url=None):
    WIDTH, HEIGHT = 1920, 1080
    canvas = Image.new('RGB', (WIDTH, HEIGHT), '#F8F8F8')
    draw = ImageDraw.Draw(canvas)

    icon_size = int(HEIGHT * 0.63)
    icon_x, icon_y = 140, 100

    app_icon = fetch_app_icon(play_store_url) if play_store_url else None

    if app_icon:
        app_icon = app_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        mask = create_rounded_rectangle_mask((icon_size, icon_size), int(icon_size * 0.22))
        rounded_icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        rounded_icon.paste(app_icon, (0, 0))
        rounded_icon.putalpha(mask)
        canvas.paste(rounded_icon, (icon_x, icon_y), rounded_icon)
    else:
        draw.rounded_rectangle(
            [(icon_x, icon_y), (icon_x + icon_size, icon_y + icon_size)],
            radius=int(icon_size * 0.22),
            fill='#E0E0E0'
        )

    # Text rendering with improved font handling
    display_name = app_name.upper()
    try:
        # Try to use a better font if available
        font = ImageFont.truetype("arial.ttf", 72)
    except IOError:
        try:
            # Try another common font
            font = ImageFont.truetype("DejaVuSans.ttf", 72)
        except IOError:
            font = ImageFont.load_default()

    # Calculate text position for better centering
    text_bbox = draw.textbbox((0, 0), display_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = icon_x + (icon_size - text_width) // 2
    text_y = icon_y + icon_size + 72
    draw.text((text_x, text_y), display_name, fill='#1A1A1A', font=font)

    # Badges - using the fallback download method
    as_badge = load_badge_from_file("app_store", width=540)
    gp_badge = load_badge_from_file("google_play", width=540)

    badge_x = WIDTH - 580  # Position badges more to the right
    if as_badge:
        canvas.paste(as_badge, (badge_x, 240), as_badge if as_badge.mode == 'RGBA' else None)
    if gp_badge:
        canvas.paste(gp_badge, (badge_x, 480), gp_badge if gp_badge.mode == 'RGBA' else None)

    return canvas

# --- STREAMLIT UI ---
st.set_page_config(page_title="CTV Tile Generator", page_icon="📺", layout="wide")
st.title("📺 CTV App Marketing Tile Generator")
st.markdown("""
    Generate professional 1920×1080 Full HD tiles for Connected TV advertising.

    **Instructions:**
    1. Enter your app name
    2. (Optional) Provide a Google Play Store URL to fetch your app icon
    3. Click "Generate Tile"
    4. Download your custom CTV marketing tile
""")

with st.sidebar:
    st.header("Settings")
    app_name = st.text_input("App Name", placeholder="My Awesome App")
    play_url = st.text_input("Google Play Store URL (Optional)",
                            placeholder="https://play.google.com/store/apps/details?id=com.example.app")

    st.markdown("---")
    st.caption("Tip: For best results, use your app's exact name as it appears in stores")
    generate_btn = st.button("Generate Tile", type="primary")

if generate_btn:
    if not app_name:
        st.error("Please enter an app name")
    else:
        with st.spinner("Creating your high-resolution tile..."):
            result_img = generate_ctv_tile(app_name, play_url)

            # Display the image
            buf = BytesIO()
            result_img.save(buf, format="PNG", quality=100)
            byte_im = buf.getvalue()

            st.image(byte_im, use_column_width=True)
            st.caption("Generated Tile: 1920×1080 Full HD (CTV Standard)")

            # Download button
            st.download_button(
                label="⬇️ Download PNG (1920×1080)",
                data=byte_im,
                file_name=f"{app_name.lower().replace(' ', '_')}_ctv_tile.png",
                mime="image/png"
            )
