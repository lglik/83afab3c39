# generate.py  (Python ≥3.9, requires `openai` and `requests`)
import os, base64, datetime, json
from openai import OpenAI

client = OpenAI()                     # expects OPENAI_API_KEY in env vars

# ----------------------------------------------------------------------
# 1. Build an imaginative prompt with GPT-4o (text model)
# ----------------------------------------------------------------------
def get_new_image_prompt() -> str:
    """Return a single, creative prompt suitable for an office display."""
    system_msg = (
        "You are a prompt-writer for an image generation model. "
        "Each time you respond, output ONE imaginative, upbeat scene that would "
        "look good in an office. Keep it under 35 words and vary the art style. "
        "Examples: 'a whimsical, high-contrast illustration of a sunrise over the Pacific "
        "in the style of Japanese woodblock prints', "
        "'a polar bear on a skateboard commuting to work, photorealistic', "
        "'retro-futuristic city skyline at dusk rendered in low-poly 3-D'."
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Give me one new prompt."},
        ],
        temperature=0.9,   # encourages variety
        max_tokens=60,
    )
    return resp.choices[0].message.content.strip()

# If IMAGE_PROMPT is pre-set, use it; otherwise generate one on the fly
PROMPT = os.getenv("IMAGE_PROMPT") or get_new_image_prompt()

# ----------------------------------------------------------------------
# 2. Generate image from the prompt
# ----------------------------------------------------------------------
def main() -> None:
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=PROMPT,
        n=1,
        size="1024x1024",
    )

    image_b64 = resp.data[0].b64_json
    png = base64.b64decode(image_b64)
    with open("83afab3c39.png", "wb") as f:
        f.write(png)

    # plain-text file with just the prompt
    with open("83afab3c39.txt", "w", encoding="utf-8") as t:
        t.write(PROMPT + "\n")

    # optional metadata
    with open("83afab3c39.json", "w") as j:
        json.dump(
            {"prompt": PROMPT,
             "generated": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"},
            j, indent=2
        )

if __name__ == "__main__":
    main()
