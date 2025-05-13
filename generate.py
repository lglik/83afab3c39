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
        "Each time you respond, output ONE imaginative, upbeat scene that would "
        "look good as framed art on a wall."
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
def shorten(txt: str, max_len: int = 60) -> str:
    """Return a short version of *txt* that fits within *max_len* chars."""
    if len(txt) <= max_len:
        return txt
    cut = txt[: max_len + 1]     # +1 so we can safely strip last word
    return cut.rsplit(" ", 1)[0] + "…"

def add_banner(png_bytes: bytes, caption: str) -> bytes:
    """Return new PNG bytes with a semi-transparent banner & caption."""
    base = Image.open(BytesIO(png_bytes)).convert("RGBA")
    w, h = base.size
    banner_h = int(h * 0.12)               # 12 % of image height
    banner_y0 = h - banner_h

    # Draw banner (black @ 50 % opacity)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, banner_y0, w, h], fill=(0, 0, 0, 128))  # 128 ≈ 50 %

    # Choose a font (falls back to default if DejaVu not present)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(banner_h * 0.5))
    except IOError:
        font = ImageFont.load_default()

    # Wrap text if it’s too wide
    margin = int(w * 0.03)
    max_text_width = w - 2 * margin
    wrapped = textwrap.fill(caption, width=40)
    txt_w, txt_h = draw.multiline_textsize(wrapped, font=font)
    text_x = (w - txt_w) // 2
    text_y = banner_y0 + (banner_h - txt_h) // 2

    draw.multiline_text(
        (text_x, text_y),
        wrapped,
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

    # Save original
    with open(f"{OUT_STEM}.png", "wb") as f:
        f.write(png_bytes)

    # Create banner version
    banner_png = add_banner(png_bytes, shorten(PROMPT))
    with open(f"{OUT_STEM}_banner.png", "wb") as f:
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
