
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import io, os, base64, requests

st.set_page_config(page_title="DigyDesign – AI Home Visualizer", page_icon="🎨", layout="wide")

# ------------- Sidebar: Settings -------------
st.sidebar.title("⚙️ Settings")
st.sidebar.markdown("**Mode:** Use local demo (no API) or try OpenAI for image generation.")
mode = st.sidebar.radio("Generation Mode", ["Local Demo (no API)", "OpenAI Images (optional)"])
openai_key = ""
if mode == "OpenAI Images (optional)":
    openai_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Needed only if you want to try real AI image generation.")
st.sidebar.markdown("---")

lang = st.sidebar.selectbox("Language / زبان", ["English", "اردو"])
st.sidebar.markdown("---")
st.sidebar.caption("© DigyDesign – Demo for Home Construction & Interior Designers")

# ------------- Helper i18n -------------
def T(en, ur):
    return ur if lang == "اردو" else en

# ------------- Header -------------
st.title(T("🏠 DigyDesign – AI Home Renovation & Interior Visualizer",
           "🏠 ڈیجی ڈیزائن – گھر کی تزئین و آرائش اور انٹیریئر ویژولائزر"))
st.write(T("Upload a room photo, choose a style, and preview an instant redesign. (Demo version)",
           "کمرے کی تصویر اپ لوڈ کریں، اسٹائل منتخب کریں، اور فوری ڈیزائن دیکھیں۔ (ڈیمو ورژن)"))

# ------------- Inputs -------------
with st.container():
    col1, col2 = st.columns([1,1])
    with col1:
        uploaded = st.file_uploader(T("Upload Room Photo", "کمرے کی تصویر اپ لوڈ کریں"),
                                    type=["jpg","jpeg","png"])
        if not uploaded:
            # show sample
            sample_path = os.path.join(os.path.dirname(__file__), "sample_room.jpg")
            img = Image.open(sample_path).convert("RGB")
            st.caption(T("No image? Using a sample room.", "اگر تصویر نہیں تو نمونہ کمرہ استعمال ہو گا"))
        else:
            img = Image.open(uploaded).convert("RGB")

        room_type = st.selectbox(T("Room Type", "کمرے کی قسم"),
                                 [T("Living Room","لِونگ روم"), T("Bedroom","بیڈ روم"), T("Kitchen","کچن"), T("Bathroom","باتھ روم")])

        style = st.selectbox(T("Design Style", "ڈیزائن اسٹائل"),
                             ["Modern", "Minimalist", "Traditional", "Luxury", "Industrial", "Scandinavian"])

        primary_color = st.color_picker(T("Primary Color Accent", "بنیادی رنگ"), "#c0a27a")

        wall_finish = st.selectbox(T("Wall Finish", "وال فنش"),
                                   ["Paint – Matte", "Paint – Satin", "Textured", "Wallpaper"])

        flooring = st.selectbox(T("Flooring", "فلورنگ"),
                                ["Keep Original", "Wood", "Marble", "Tile"])

        generate = st.button(T("Generate Redesign", "ڈیزائن بنائیں"), type="primary", use_container_width=True)

    with col2:
        st.markdown(T("### Output", "### نتیجہ"))
        placeholder = st.empty()

# ------------- Image Utilities -------------
def color_grade(image, style, primary_hex):
    # simple aesthetic changes per style
    img = image.copy()
    enh_contrast = ImageEnhance.Contrast(img)
    enh_bright = ImageEnhance.Brightness(img)
    enh_color = ImageEnhance.Color(img)

    if style == "Modern":
        img = enh_contrast.enhance(1.2)
        img = enh_bright.enhance(1.05)
        img = enh_color.enhance(1.05)
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    elif style == "Minimalist":
        img = enh_color.enhance(0.9)
        img = enh_contrast.enhance(1.1)
        img = img.filter(ImageFilter.GaussianBlur(0.2))
    elif style == "Traditional":
        img = enh_color.enhance(1.05)
        img = enh_bright.enhance(1.03)
        img = ImageEnhance.Contrast(img).enhance(1.08)
    elif style == "Luxury":
        img = enh_bright.enhance(1.08)
        img = enh_contrast.enhance(1.15)
        img = enh_color.enhance(1.12)
    elif style == "Industrial":
        img = enh_color.enhance(0.85)
        img = enh_contrast.enhance(1.25)
    elif style == "Scandinavian":
        img = enh_bright.enhance(1.10)
        img = enh_contrast.enhance(1.08)
        img = enh_color.enhance(1.0)

    # apply a subtle color tone toward primary_hex
    r = int(primary_hex[1:3], 16)
    g = int(primary_hex[3:5], 16)
    b = int(primary_hex[5:7], 16)
    tint = Image.new("RGB", img.size, (r, g, b))
    img = Image.blend(img, tint, alpha=0.06)
    return img

def overlay_floor(image, flooring):
    if flooring == "Keep Original":
        return image
    base = image.copy()
    W, H = base.size
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if flooring == "Wood":
        tex = Image.open(os.path.join(assets_dir, "floor_wood.jpg")).resize((W,H))
    elif flooring == "Marble":
        tex = Image.open(os.path.join(assets_dir, "floor_marble.jpg")).resize((W,H))
    else:
        tex = Image.open(os.path.join(assets_dir, "floor_tile.jpg")).resize((W,H))

    # Fake "floor area": lower 40%
    floor_y = int(H*0.6)
    crop = tex.crop((0, floor_y, W, H))
    base_crop = base.crop((0, floor_y, W, H))
    blended = Image.blend(base_crop, crop, alpha=0.45)
    base.paste(blended, (0, floor_y))
    # add slight perspective shadow at boundary
    return base

def try_openai(img, prompt, openai_key):
    # Minimal call using Images API v1 if key provided
    try:
        import requests, base64, io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        headers = {"Authorization": f"Bearer {openai_key}"}
        data = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "size": "1024x1024",
            "image": img_b64
        }
        r = requests.post("https://api.openai.com/v1/images/edits", headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            out = r.json()
            if "data" in out and len(out["data"])>0 and "b64_json" in out["data"][0]:
                b = base64.b64decode(out["data"][0]["b64_json"])
                return Image.open(io.BytesIO(b)).convert("RGB")
        st.warning(f"OpenAI response: {r.status_code} – falling back to local demo.")
    except Exception as ex:
        st.info(f"OpenAI call failed: {ex}. Using local demo instead.")
    return None

# ------------- Product Suggestions (mock) -------------
def suggest_products(style, room_type):
    # Basic, local-market styled suggestions for Pakistan
    items = [
        {"name":"Interwood – Oslo 3-Seater Sofa", "style":"Modern", "room":"Living Room", "price":"PKR 165,000", "link":"https://www.interwood.pk/"},
        {"name":"Habitt – Minimal Coffee Table", "style":"Minimalist", "room":"Living Room", "price":"PKR 42,000", "link":"https://www.habitt.com/"},
        {"name":"ChenOne – Persian Rug 8x10", "style":"Traditional", "room":"Living Room", "price":"PKR 78,500", "link":"https://www.chenone.com/"},
        {"name":"StoneWorld – Calacatta Marble Slab", "style":"Luxury", "room":"Kitchen", "price":"PKR 9,500 / sq.ft", "link":"https://www.facebook.com/stoneworldpakistan/"},
        {"name":"Metro – Industrial Pendant Light", "style":"Industrial", "room":"Kitchen", "price":"PKR 12,800", "link":"https://www.metro-online.pk/"},
        {"name":"Ikea (import) – Billy Bookcase", "style":"Scandinavian", "room":"Living Room", "price":"PKR 45,000 est.", "link":"https://www.ikea.com/"},
    ]
    out = [x for x in items if x["style"]==style and room_type.split()[0] in x["room"]]
    if not out:
        out = [x for x in items if x["style"]==style]
    return out[:3]

# ------------- Main Generation -------------
if generate:
    with st.spinner(T("Generating design...", "ڈیزائن تیار ہو رہا ہے...")):
        prompt = f"Redesign this {room_type} in {style} style with {wall_finish}, primary color {primary_color}, flooring {flooring}."
        result_img = None
        if mode == "OpenAI Images (optional)" and openai_key.strip():
            result_img = try_openai(img, prompt, openai_key)

        if result_img is None:
            # Local transformation demo
            demo = color_grade(img, style, primary_color)
            demo = overlay_floor(demo, flooring)
            result_img = demo

        # Display side-by-side + download
        c1, c2 = st.columns(2)
        with c1:
            st.image(img, caption=T("Before", "پہلے"), use_container_width=True)
        with c2:
            st.image(result_img, caption=T("After (AI Preview)", "بعد میں (اے آئی پریویو)"), use_container_width=True)

        # Download button
        buf = io.BytesIO()
        result_img.save(buf, format="JPEG", quality=92)
        st.download_button(T("Download Result", "نتیجہ ڈاؤن لوڈ کریں"), buf.getvalue(), file_name="ai_redesign.jpg", mime="image/jpeg")

        # Suggestions
        st.markdown(T("### Suggested Products (Pakistan)","### مجوزہ مصنوعات (پاکستان)"))
        recs = suggest_products(style, room_type)
        for r in recs:
            st.markdown(f"- **{r['name']}** — {r['price']} · [View]({r['link']})")

else:
    st.info(T("Upload an image and click **Generate Redesign** to see results.",
              "تصویر اپ لوڈ کریں اور **ڈیزائن بنائیں** پر کلک کریں۔"))

st.markdown("---")
st.markdown(T("**Tip:** For a more realistic demo, use a bright, evenly-lit room photo.",
              "**ٹِپ:** بہتر نتیجے کے لیے روشن، یکساں روشنی والی کمرے کی تصویر استعمال کریں۔"))
