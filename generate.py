# generate.py  (Python ≥3.9, requires `openai`, `requests`, and `pillow`)
import os, base64, datetime, json, textwrap
from openai import OpenAI

# NEW: for banner creation
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

client = OpenAI()                     # expects OPENAI_API_KEY in env vars
OUT_STEM = "83afab3c39"               # change if you want unique filenames

# ----------------------------------------------------------------------
# 1. Build an imaginative prompt with GPT-4o (text model)
# ----------------------------------------------------------------------
def get_new_image_prompt() -> str:
    """Return a single, creative prompt suitable for an office display."""
    system_msg = (
        "You are a prompt-writer for an image generation model. "
        "Each time you respond, output ONE imaginative, upbeat scene that looks "
        "like a painting, woodblock, or other piece of physical artwork that might be framed on a wall. Keep the prompt to 20 words or fewer."
        "Take into account that the image will be displayed on a 5.65inch ACeP 7-Color E-Paper E-Ink Display Module"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Give me one new prompt."},
        ],
        temperature=0.9,
        max_tokens=60,
    )
    return resp.choices[0].message.content.strip()

# If IMAGE_PROMPT is pre-set, use it; otherwise generate one on the fly
PROMPT = os.getenv("IMAGE_PROMPT") or get_new_image_prompt()

# ----------------------------------------------------------------------
# 2. Helpers
# ----------------------------------------------------------------------

def add_banner(png_bytes: bytes, caption: str) -> bytes:
    """
    Return PNG bytes with a fixed-height (12 %) semi-transparent banner
    at the bottom and a centered caption.  If the text is too tall or
    wide, the font size is reduced until it fits.
    """
    base = Image.open(BytesIO(png_bytes)).convert("RGBA")
    w, h = base.size

    banner_h   = int(h * 0.12)          # fixed height (no expansion)
    banner_y0  = h - banner_h
    margin     = int(w * 0.03)          # side/top/bottom padding
    max_width  = w - 2 * margin
    max_height = banner_h - 2 * margin

    # Draw the banner rectangle first
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    draw.rectangle([0, banner_y0, w, h], fill=(0, 0, 0, 128))  # 50 % black

    # Helper to get a truetype font or default fallback
    def make_font(px: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", px)
        except IOError:
            return ImageFont.load_default()

    # Start with a font size ~55 % of banner height and shrink as needed
    font_px = int(banner_h * 0.55)
    font    = make_font(font_px)

    # Word-wrap once at 40 chars; later only font size shrinks
    wrapped_caption = textwrap.fill(caption, width=40)

    while True:
        # Measure bounding box for the wrapped text
        try:
            bbox = draw.multiline_textbbox((0, 0), wrapped_caption, font=font)
            txt_w, txt_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:  # Pillow <8
            txt_w, txt_h = draw.multiline_textsize(wrapped_caption, font=font)

        if txt_w <= max_width and txt_h <= max_height:
            break  # fits!

        # Reduce font size and try again; stop at a safe minimum
        font_px -= 2
        if font_px < 10:
            break
        font = make_font(font_px)

    # Center text within the banner
    text_x = (w - txt_w) // 2
    text_y = banner_y0 + (banner_h - txt_h) // 2

    draw.multiline_text(
        (text_x, text_y),
        wrapped_caption,
        font=font,
        fill=(255, 255, 255, 230),
        align="center",
    )

    composed = Image.alpha_composite(base, overlay)
    buf = BytesIO()
    composed.save(buf, format="PNG")
    return buf.getvalue()

# ----------------------------------------------------------------------
# 3. Generate image from the prompt and post-process
# ----------------------------------------------------------------------
def main() -> None:
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=PROMPT,
        n=1,
        size="1024x1024",
    )

    image_b64 = resp.data[0].b64_json
    png_bytes = base64.b64decode(image_b64)

    # Create png with banner
    banner_png = add_banner(png_bytes, PROMPT)
    with open(f"{OUT_STEM}.png", "wb") as f:
        f.write(banner_png)

    # Plain-text file with just the prompt
    with open(f"{OUT_STEM}.txt", "w", encoding="utf-8") as t:
        t.write(PROMPT + "\n")

    # Optional metadata
    with open(f"{OUT_STEM}.json", "w") as j:
        json.dump(
            {
                "prompt": PROMPT,
                "generated": datetime.datetime.utcnow()
                .isoformat(timespec="seconds")
                + "Z",
            },
            j,
            indent=2,
        )

if __name__ == "__main__":
    main()
