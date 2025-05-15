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
        "Take into account that the image will be displayed on a 5.65inch ACeP 7-Color E-Paper E-Ink Display Module."
        "Do not do nightime or other images that are too dark since the display has no built in lighting."
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
    at the bottom and a caption that is automatically scaled to use the
    full banner area (width *and* height) without overflowing.
    """
    base = Image.open(BytesIO(png_bytes)).convert("RGBA")
    w, h = base.size

    banner_h   = int(h * 0.12)            # fixed banner height
    banner_y0  = h - banner_h
    margin     = int(w * 0.03)            # inner padding on all sides
    max_width  = w - 2 * margin
    max_height = banner_h - 2 * margin

    # --- draw dark translucent banner ---------------------------------
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    draw.rectangle([0, banner_y0, w, h], fill=(0, 0, 0, 128))   # 50 % black

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def make_font(px: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", px)
        except IOError:                       # fall back to built-in bitmap
            return ImageFont.load_default()

    def wrap_to_pixels(text: str, font: ImageFont.FreeTypeFont) -> str:
        """
        Greedy word-wrap that inserts line-breaks so no line exceeds
        `max_width` in rendered pixel length.
        """
        lines, current = [], []
        for word in text.split():
            test = " ".join(current + [word])
            if draw.textlength(test, font=font) <= max_width:
                current.append(word)
            else:                              # start new line
                lines.append(" ".join(current))
                current = [word]
        lines.append(" ".join(current))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # choose the *largest* font that still fits (binary search)
    # ------------------------------------------------------------------
    low, high = 10, max_height           # px bounds; 10 is safe minimum
    best_font, best_text, best_bbox = None, None, None

    while low <= high:
        mid   = (low + high) // 2
        font  = make_font(mid)
        text  = wrap_to_pixels(caption, font)
        bbox  = draw.multiline_textbbox((0, 0), text, font=font)

        txt_w, txt_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if txt_w <= max_width and txt_h <= max_height:
            # fits – try a *larger* font
            best_font, best_text, best_bbox = font, text, (txt_w, txt_h)
            low = mid + 1
        else:
            # too large – shrink
            high = mid - 1

    # safety fallback (should never trigger)
    if best_font is None:
        best_font = make_font(10)
        best_text = wrap(caption, width=40)
        txt_w, txt_h = draw.multiline_textbbox((0, 0), best_text, font=best_font)[2:]
    else:
        txt_w, txt_h = best_bbox

    # ------------------------------------------------------------------
    # render
    # ------------------------------------------------------------------
    text_x = (w - txt_w) // 2
    text_y = banner_y0 + (banner_h - txt_h) // 2

    draw.multiline_text(
        (text_x, text_y),
        best_text,
        font=best_font,
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
