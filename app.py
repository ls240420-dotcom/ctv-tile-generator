import streamlit as st
from PIL import Image, ImageDraw
from io import BytesIO
import requests
import re

# --- Constants ---
TILE_WIDTH, TILE_HEIGHT = 480, 270  
ICON_SIZE = int(TILE_HEIGHT * 0.75) # Slightly larger icon since text is gone
BADGE_WIDTH = 180  

# --- Helper Functions ---
def extract_app_id(play_store_url):
    match = re.search(r'id=([^&]+)', play_store_url)
    return match.group(1) if match else None

def fetch_app_icon(play_store_url):
    try:
        app_id = extract_app_id(play_store_url)
        if not app_id:
            return None
        response = requests.get(f'https://play.google.com/store/apps/details?id={app_id}')
        icon_match = re.search(r'https://play-lh\.googleusercontent\.com/[^"]+', response.text)
        if icon_match:
            icon_url = re.sub(r'=s\d+', '=s512', icon_match.group(0))
            icon_response = requests.get(icon_url)
            return Image.open(BytesIO(icon_response.content))
    except Exception as e:
        st.error(f"Failed to fetch icon: {e}")
        return None

def create_rounded_rectangle_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def load_badge(badge_type, width=BADGE_WIDTH):
    try:
        # Using official fallback URLs directly to keep code standalone
        urls = {
            'app_store': 'https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us',
            'google_play': 'https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png'
        }
        response = requests.get(urls[badge_type], timeout=10)
        badge = Image.open(BytesIO(response.content)).convert("RGBA")
        aspect_ratio = badge.height / badge.width
        return badge.resize((width * 2, int(width * 2 * aspect_ratio)), Image.Resampling.LANCZOS)
    except Exception as e:
        st.error(f"Failed to load {badge_type} badge: {e}")
        return None

def generate_ctv_tile(play_store_url=None):
    # Render at 2x resolution
    canvas = Image.new('RGB', (TILE_WIDTH * 2, TILE_HEIGHT * 2), '#F8F8F8')
    draw = ImageDraw.Draw(canvas)

    # --- Icon (Left Side) ---
    icon_size = ICON_SIZE * 2
    icon_x, icon_y = 40 * 2, (TILE_HEIGHT * 2 - icon_size) // 2 # Centered vertically
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
            fill='#00D4AA'
        )

    # --- Badges (Right Side) ---
    as_badge = load_badge('app_store')
    gp_badge = load_badge('google_play')

    badge_x = TILE_WIDTH * 2 - BADGE_WIDTH * 2 - 40 * 2
    if as_badge:
        canvas.paste(as_badge, (badge_x, TILE_HEIGHT * 2 // 2 - 85 * 2), as_badge)
    if gp_badge:
        canvas.paste(gp_badge, (badge_x, TILE_HEIGHT * 2 // 2 + 5 * 2), gp_badge)

    # Downsample
    canvas = canvas.resize((TILE_WIDTH, TILE_HEIGHT), Image.Resampling.LANCZOS)
    return canvas

# --- Streamlit UI ---
st.set_page_config(page_title="Samsung Ads CTV Tile Generator", page_icon="📺")
st.title("📺 Samsung Ads CTV Tile Generator")

with st.sidebar:
    st.header("App Details")
    play_store_url = st.text_input(
        "Google Play URL",
        placeholder="https://play.google.com/store/apps/details?id=com.example"
    )
    generate_btn = st.button("Generate Tile", type="primary")

if generate_btn:
    with st.spinner("Generating..."):
        tile = generate_ctv_tile(play_store_url)
        buf = BytesIO()
        tile.save(buf, format="PNG")

        st.image(buf, caption="Font-Free CTV Tile", use_column_width=True)
        st.download_button(
            label="⬇ Download PNG",
            data=buf.getvalue(),
            file_name="ctv_tile.png",
            mime="image/png"
        )
