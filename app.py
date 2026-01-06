import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re
import base64

# --- HELPER FUNCTIONS ---

def extract_app_id(play_store_url):
    match = re.search(r'id=([^&]+)', play_store_url)
    return match.group(1) if match else None

def fetch_app_icon(play_store_url):
    try:
        app_id = extract_app_id(play_store_url)
        if not app_id: return None
        response = requests.get(f'https://play.google.com/store/apps/details?id={app_id}')
        icon_match = re.search(r'https://play-lh\.googleusercontent\.com/[^"]+', response.text)
        if icon_match:
            # Request higher resolution icon (up to 512px)
            icon_url = re.sub(r'=s\d+', '=s512', icon_match.group(0))
            icon_response = requests.get(icon_url)
            return Image.open(BytesIO(icon_response.content))
    except:
        return None

def create_rounded_rectangle_mask(size, radius):
    # Use higher quality antialiasing
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def download_official_badge(badge_type, width=540):  # Increased badge size for 1920x1080
    urls = {
        'app_store': 'https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us',
        'google_play': 'https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png'
    }
    try:
        response = requests.get(urls[badge_type], timeout=10)
        badge = Image.open(BytesIO(response.content))
        aspect_ratio = badge.height / badge.width
        return badge.resize((width, int(width * aspect_ratio)), Image.Resampling.LANCZOS)
    except:
        return None

def generate_ctv_tile(app_name, play_store_url=None):
    # CTV Standard: 1920x1080 (Full HD 16:9)
    WIDTH, HEIGHT = 1920, 1080
    
    # Create canvas with higher quality
    canvas = Image.new('RGB', (WIDTH, HEIGHT), '#F8F8F8')
    draw = ImageDraw.Draw(canvas)
    
    # Scale all elements proportionally
    icon_size = int(HEIGHT * 0.63)  # ~680px
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
        draw.rounded_rectangle([(icon_x, icon_y), (icon_x + icon_size, icon_y + icon_size)], 
                               radius=int(icon_size * 0.22), fill='#E0E0E0')

    # Text with higher resolution font
    display_name = app_name.upper()
    try:
        # For production: upload a .ttf font file to your app directory
        # font = ImageFont.truetype("Arial.ttf", 72)
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    draw.text((icon_x, icon_y + icon_size + 72), display_name, fill='#1A1A1A', font=font)
    
    # Badges - scaled up for 1920x1080
    as_badge = download_official_badge('app_store', width=540)
    gp_badge = download_official_badge('google_play', width=540)
    
    badge_x = 1260
    if as_badge: 
        canvas.paste(as_badge, (badge_x, 240), as_badge if as_badge.mode == 'RGBA' else None)
    if gp_badge: 
        canvas.paste(gp_badge, (badge_x, 480), gp_badge if gp_badge.mode == 'RGBA' else None)
    
    return canvas

# --- STREAMLIT UI ---

st.set_page_config(page_title="CTV Tile Generator", page_icon="📺", layout="wide")
st.title("📺 CTV App Marketing Tile Generator")
st.write("Generate professional 1920x1080 Full HD tiles for Connected TV advertising.")

with st.sidebar:
    st.header("Settings")
    app_name = st.text_input("App Name", "My Awesome App")
    play_url = st.text_input("Play Store URL (Optional)")
    generate_btn = st.button("Generate Tile", type="primary")

if generate_btn:
    with st.spinner("Creating your high-resolution tile..."):
        result_img = generate_ctv_tile(app_name, play_url)
        
        # High-quality display using base64 encoding to preserve resolution
        buf = BytesIO()
        result_img.save(buf, format="PNG", optimize=False, quality=100)
        byte_im = buf.getvalue()
        
        # Display with HTML for better quality control
        image_b64 = base64.b64encode(byte_im).decode()
        st.markdown(
            f"<img style='max-width: 100%; height: auto;' src='data:image/png;base64, {image_b64}' alt='Generated CTV Tile'/>",
            unsafe_allow_html=True
        )
        
        st.caption("Generated Tile: 1920x1080 Full HD (CTV Standard)")
        
        # Download button
        st.download_button(
            label="Download PNG (1920x1080)",
            data=byte_im,
            file_name=f"{app_name.lower().replace(' ', '_')}_ctv_tile.png",
            mime="image/png"
        )
