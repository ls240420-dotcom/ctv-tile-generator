import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import re

# --- Constants ---
TILE_WIDTH, TILE_HEIGHT = 480, 270  # CTV standard (16:9)
ICON_SIZE = int(TILE_HEIGHT * 0.7)  # Icon fills ~70% of height
BADGE_WIDTH = 180  # Width for each badge

# --- Helper Functions ---
def extract_app_id(play_store_url):
    match = re.search(r'id=([^&]+)', play_store_url)
    return match.group(1) if match else None

def fetch_app_icon(play_store_url):
    try:
        app_id = extract_app_id(play_store_url)
        if not app_id:
            st.warning("Invalid Play Store URL. Using placeholder icon.")
            return None
        response = requests.get(f'https://play.google.com/store/apps/details?id={app_id}')
        icon_match = re.search(r'https://play-lh\.googleusercontent\.com/[^"]+', response.text)
        if icon_match:
            icon_url = re.sub(r'=s\d+', '=s512', icon_match.group(0))  # Fetch highest-res icon
            icon_response = requests.get(icon_url)
            return Image.open(BytesIO(icon_response.content))
    except Exception as e:
        st.error(f"Failed to fetch icon: {e}. Using placeholder.")
        return None

def create_rounded_rectangle_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def load_badge(badge_type, width=BADGE_WIDTH):
    try:
        # Load your pre-converted PNG badges
        filename = {
            'app_store': "Download_on_the_App_Store_Badge_US-UK_RGB_blk_092917.png",
            'google_play': "GetItOnGooglePlay_Badge_Web_color_English.png"
        }[badge_type]
        badge = Image.open(filename)
        aspect_ratio = badge.height / badge.width
        return badge.resize((width * 2, int(width * 2 * aspect_ratio)), Image.Resampling.LANCZOS)
    except Exception as e:
        st.error(f"Failed to load {badge_type} badge: {e}. Using fallback.")
        # Fallback to official badges if local files fail
        urls = {
            'app_store': 'https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us',
            'google_play': 'https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png'
        }
        response = requests.get(urls[badge_type], timeout=10)
        badge = Image.open(BytesIO(response.content))
        aspect_ratio = badge.height / badge.width
        return badge.resize((width * 2, int(width * 2 * aspect_ratio)), Image.Resampling.LANCZOS)

def generate_ctv_tile(app_name, play_store_url=None):
    # Render at 2x resolution for sharpness, then downsample
    canvas = Image.new('RGB', (TILE_WIDTH * 2, TILE_HEIGHT * 2), '#F8F8F8')  # Light gray background
    draw = ImageDraw.Draw(canvas)

    # --- Icon (Left Side) ---
    icon_size = ICON_SIZE * 2  # 2x for high-res
    icon_x, icon_y = 40 * 2, 30 * 2
    app_icon = fetch_app_icon(play_store_url) if play_store_url else None

    if app_icon:
        app_icon = app_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        mask = create_rounded_rectangle_mask((icon_size, icon_size), int(icon_size * 0.22))
        rounded_icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        rounded_icon.paste(app_icon, (0, 0))
        rounded_icon.putalpha(mask)
        canvas.paste(rounded_icon, (icon_x, icon_y), rounded_icon)
    else:
        # Placeholder (Kalshi green as default)
        draw.rounded_rectangle(
            [(icon_x, icon_y), (icon_x + icon_size, icon_y + icon_size)],
            radius=int(icon_size * 0.22),
            fill='#00D4AA'  # Kalshi's brand color
        )

    # --- App Name (Centered Under Icon) ---
    display_name = app_name.upper()
    try:
        font = ImageFont.truetype("arialbd.ttf", 40 * 2)  # Bold font for CPI emphasis
    except:
        font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), display_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = icon_x + (icon_size - text_width) // 2
    draw.text((text_x, icon_y + icon_size + 20 * 2), display_name, fill='black', font=font)

    # --- Badges (Right Side, Stacked Vertically) ---
    as_badge = load_badge('app_store')
    gp_badge = load_badge('google_play')

    badge_x = TILE_WIDTH * 2 - BADGE_WIDTH * 2 - 20 * 2
    if as_badge:
        canvas.paste(as_badge, (badge_x, TILE_HEIGHT * 2 // 2 - 80 * 2), as_badge)
    if gp_badge:
        canvas.paste(gp_badge, (badge_x, TILE_HEIGHT * 2 // 2 + 20 * 2), gp_badge)

    # --- CPI-Focused CTA ---
    cta = "TAP TO INSTALL"
    cta_font = ImageFont.truetype("arialbd.ttf", 20 * 2) if "arialbd.ttf" in ImageFont.list() else ImageFont.load_default()
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_width = cta_bbox[2] - cta_bbox[0]
    cta_x = badge_x + (BADGE_WIDTH * 2 - cta_width) // 2
    draw.text((cta_x, TILE_HEIGHT * 2 - 50 * 2), cta, fill='black', font=cta_font)

    # Downsample to final resolution
    canvas = canvas.resize((TILE_WIDTH, TILE_HEIGHT), Image.Resampling.LANCZOS)
    return canvas

# --- Streamlit UI ---
st.set_page_config(page_title="Samsung Ads CTV Tile Generator", page_icon="📺", layout="wide")
st.title("📺 Samsung Ads CTV Tile Generator (480×270)")
st.markdown(f"""
    **For Your CTV-to-Mobile CPI Campaigns**
    - **480×270 resolution** (16:9 standard for CTV).
    - Optimized for **high conversions** on Samsung Ads.
    - Includes **App Store + Google Play badges** (using your PNG files).
""")

with st.sidebar:
    st.header("App Details")
    app_name = st.text_input("App Name", value="Kalshi")
    play_store_url = st.text_input(
        "Google Play URL (for icon only)",
        placeholder="https://play.google.com/store/apps/details?id=com.example"
    )
    generate_btn = st.button("Generate Tile", type="primary")

if generate_btn:
    if not app_name:
        st.error("Please enter an app name.")
    else:
        with st.spinner("Generating high-res CTV tile..."):
            tile = generate_ctv_tile(app_name, play_store_url)
            buf = BytesIO()
            tile.save(buf, format="PNG", quality=100, dpi=(300, 300))  # High DPI for sharpness

            # Display and download
            st.image(buf, caption="CTV Tile (480×270, High-Res)", use_column_width=True)
            st.download_button(
                label="⬇ Download PNG",
                data=buf.getvalue(),
                file_name=f"{app_name.lower().replace(' ', '_')}_ctv_tile.png",
                mime="image/png"
            )
            st.success("✅ Tile generated! Optimized for CPI conversions on Samsung Ads.")

