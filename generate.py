# generate.py  (Python ≥3.9, requires `openai` and `requests`)
import os, requests, datetime, json
from openai import OpenAI

PROMPT = os.getenv(
    "IMAGE_PROMPT",
    "A whimsical, high-contrast illustration of a sunrise over the Pacific Ocean, "
    "in the style of Japanese woodblock prints"
)

def main():
    client = OpenAI()                       # uses env var OPENAI_API_KEY
    resp = client.images.generate(          # or client.images.create for DALLE-3
        model="gpt-image-1",
        prompt=PROMPT,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    url = resp.data[0].url
    img = requests.get(url, timeout=30).content
    with open("83afab3c39.png", "wb") as f:
        f.write(img)
    # Add metadata file so every commit has a diff even if the art is identical
    meta = {
        "prompt": PROMPT,
        "generated": datetime.datetime.utcnow().isoformat() + "Z",
        "source_url": url
    }
    with open("daily.json", "w") as m:
        json.dump(meta, m, indent=2)

if __name__ == "__main__":
    main()
