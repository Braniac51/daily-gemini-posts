import os
import json
import base64
import requests
from pathlib import Path

# Config
API_KEY = os.environ.get("GEMINI_API_KEY")
OUTPUT_DIR = Path("generated")
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_MODEL = "gemini-2.5-image"  # placeholder; replace if your provider uses another
GEMINI_ENDPOINT = "https://api.example.com/v1/generate"  # REPLACE with your real Gemini endpoint

def build_prompt():
    return (
        "Create 5 square Instagram-style images for a small business. "
        "Return a JSON array named posts with exactly 5 objects. "
        "Each object must contain: title, image_base64 or image_url, caption, hashtags. "
        "Captions 20-40 words; 6-10 trending hashtags each."
    )

def call_gemini(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GEMINI_MODEL,
        "prompt": prompt,
        "max_tokens": 1200,
        "temperature": 0.8,
    }
    resp = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()

def parse_response(resp):
    # Try several common shapes; adapt if your provider returns a different structure
    if isinstance(resp, dict) and "posts" in resp:
        return resp["posts"]
    # Sometimes the text is returned as a string field
    for key in ("output", "result", "text"):
        if isinstance(resp, dict) and key in resp and isinstance(resp[key], str):
            try:
                parsed = json.loads(resp[key])
                if isinstance(parsed, dict) and "posts" in parsed:
                    return parsed["posts"]
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
    raise RuntimeError("Could not parse posts array from Gemini response. Inspect raw_response.json to adapt parser.")

def save_items(posts):
    out = []
    for i, item in enumerate(posts[:5], start=1):
        title = item.get("title", f"Post {i}")
        caption = item.get("caption", "")
        hashtags = item.get("hashtags", [])
        img_b64 = item.get("image_base64")
        img_data = None
        if img_b64:
            img_data = base64.b64decode(img_b64.split(",")[-1])
        else:
            image_url = item.get("image_url")
            if image_url:
                img_data = requests.get(image_url).content
            else:
                raise RuntimeError(f"No image provided for post {i}")
        image_name = OUTPUT_DIR / f"post_{i}.png"
        with open(image_name, "wb") as f:
            f.write(img_data)
        out.append({
            "image_path": str(image_name),
            "title": title,
            "caption": caption,
            "hashtags": hashtags
        })
    out_file = OUTPUT_DIR / "posts.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(out)} posts to {out_file}")
    return out_file

def main():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")
    prompt = build_prompt()
    raw = call_gemini(prompt)
    Path(OUTPUT_DIR / "raw_response.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    posts = parse_response(raw)
    save_items(posts)

if __name__ == "__main__":
    main()
