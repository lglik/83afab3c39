# generate.py  (Python ≥3.9, requires `openai` and `requests`)
import os, requests, datetime, json
from openai import OpenAI


PROMPT = os.getenv(
    "IMAGE_PROMPT",
    "A whimsical, high-contrast illustration of a sunrise over the Pacific Ocean, "
    "in the style of Japanese woodblock prints"
)

def main():
    client = OpenAI()
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=PROMPT,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    url = resp.data[0].url
    png = requests.get(url, timeout=30).content
    with open("83afab3c39.png", "wb") as f:
        f.write(png)

    # ↓ NEW: plain-text page containing only the prompt (one line)
    with open("83afab3c39.txt", "w", encoding="utf-8") as t:
        t.write(PROMPT + "\n")

    # (optional) JSON metadata still useful if you want it
    with open("83afab3c39.json", "w") as j:
        json.dump(
            {"prompt": PROMPT, "generated": datetime.datetime.utcnow().isoformat() + "Z", "source_url": url},
            j, indent=2
        )
        

if __name__ == "__main__":
    main()
