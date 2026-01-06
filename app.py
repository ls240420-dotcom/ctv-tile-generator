import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re

# --- HELPER FUNCTIONS (Your original logic) ---

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
            icon_url = re.sub(r'=s\d+', '=s512', icon_match.group(0))
            icon_response = requests.get(icon_url)
            return Image.open(BytesIO(icon_response.content))
    except:
        return None

def create_rounded_rectangle_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def download_official_badge(badge_type, width=135):
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
    WIDTH, HEIGHT = 480, 270
    canvas = Image.new('RGB', (WIDTH, HEIGHT), '#F8F8F8')
    draw = ImageDraw.Draw(canvas)
    
    icon_size = int(HEIGHT * 0.63)
    icon_x, icon_y = 35, 25
    
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

    # Text rendering (using default font for simplicity in web environment)
    display_name = app_name.upper()
    try:
        font = ImageFont.load_default() # In a real app, upload a .ttf to your folder
    except:
        font = ImageFont.load_default()
        
    draw.text((icon_x, icon_y + icon_size + 18), display_name, fill='#1A1A1A', font=font)
    
    # Badges
    as_badge = download_official_badge('app_store')
    gp_badge = download_official_badge('google_play')
    
    if as_badge: canvas.paste(as_badge, (315, 60), as_badge if as_badge.mode == 'RGBA' else None)
    if gp_badge: canvas.paste(gp_badge, (315, 120), gp_badge if gp_badge.mode == 'RGBA' else None)
    
    return canvas

# --- STREAMLIT UI ---

st.set_page_config(page_title="CTV Tile Generator", page_icon="📺")
st.title("📺 CTV App Marketing Tile Generator")
st.write("Enter your app details below to generate a 480x270 marketing tile.")

with st.sidebar:
    st.header("Settings")
    app_name = st.text_input("App Name", "My Awesome App")
    play_url = st.text_input("Play Store URL (Optional)")
    generate_btn = st.button("Generate Tile", type="primary")

if generate_btn:
    with st.spinner("Creating your tile..."):
        result_img = generate_ctv_tile(app_name, play_url)
        
        # Display the image
        st.image(result_img, caption="Generated Tile", use_container_width=True)
        
        # Download button
        buf = BytesIO()
        result_img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="Download Image",
            data=byte_im,
            file_name=f"{app_name.lower().replace(' ', '_')}_tile.png",
            mime="image/png"
        )
