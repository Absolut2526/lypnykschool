import urllib.request
import ssl
import re
import os
import json
import time
import urllib.parse

ctx = ssl._create_unverified_context()
BASE_URL = "https://sites.google.com/view/lypnykzosh"
DATA_DIR = "/Users/pc/lypnyk-school/data"
IMAGES_DIR = "/Users/pc/lypnyk-school/assets/images"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

def encode_url(url_str):
    url_unquoted = urllib.parse.unquote(url_str)
    parsed = urllib.parse.urlsplit(url_unquoted)
    encoded_path = urllib.parse.quote(parsed.path, safe='/:@&=+$,~')
    encoded_query = urllib.parse.quote(parsed.query, safe='/:@&=+$,~')
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, encoded_query, parsed.fragment))

def fetch_url(url):
    enc_url = encode_url(url)
    req = urllib.request.Request(
        enc_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {enc_url}: {e}")
        return None

visited_urls = set()
to_visit = ["https://sites.google.com/view/lypnykzosh/головна-сторінка"]
all_pages_data = []
all_image_urls = set()

print("Starting crawling with clean UTF-8 URL encoding...")

while to_visit:
    current_url = to_visit.pop(0)
    clean_url = urllib.parse.unquote(current_url).split('?')[0].rstrip('/')
    if clean_url in visited_urls:
        continue
    visited_urls.add(clean_url)

    print(f"[{len(visited_urls)}] Crawling: {clean_url}")
    html = fetch_url(clean_url)
    if not html:
        continue

    # Extract title
    title_m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    page_title = title_m.group(1).strip() if title_m else ""
    if " - " in page_title:
        page_title = page_title.split(" - ")[0].strip()

    # Extract all links
    links = re.findall(r'href=[\"\']([^\"\']+)[\"\']', html)
    for l in links:
        l_unquote = urllib.parse.unquote(l)
        if '/view/lypnykzosh' in l_unquote:
            full = "https://sites.google.com" + l if l.startswith('/') else l
            clean_f = urllib.parse.unquote(full).split('?')[0].rstrip('/')
            if clean_f not in visited_urls and clean_f not in [urllib.parse.unquote(x).split('?')[0].rstrip('/') for x in to_visit]:
                to_visit.append(clean_f)

    # Extract Google Drive / Docs / external links / forms / videos
    doc_links = []
    for l in links:
        if any(k in l for k in ['drive.google.com', 'docs.google.com', 'forms.gle', '.pdf', '.docx', '.xlsx', 'facebook.com', 'youtube.com']):
            doc_links.append(l)

    # Extract images
    imgs = re.findall(r'src=[\"\'](https://lh\d+\.googleusercontent\.com/[^\"\']+|https://sites\.google\.com/sitesv-images-rt/[^\"\']+)[\"\']', html)
    for img in imgs:
        all_image_urls.add(img)

    # Clean text content
    text_content = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text_content = re.sub(r'<style.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract blocks
    raw_texts = re.findall(r'>([^<]+)<', text_content)
    cleaned_texts = []
    for t in raw_texts:
        t_clean = t.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&amp;', '&').strip()
        if len(t_clean) > 0 and not t_clean.startswith('{') and not t_clean.startswith('var ') and not t_clean.startswith('.M63') and not t_clean.startswith('/*') and not t_clean.startswith('window.'):
            cleaned_texts.append(t_clean)

    all_pages_data.append({
        "url": clean_url,
        "slug": clean_url.replace(BASE_URL, '').strip('/'),
        "title": page_title,
        "texts": cleaned_texts,
        "doc_links": list(set(doc_links)),
        "images": list(set(imgs))
    })

    time.sleep(0.1)

print(f"\nCrawled {len(all_pages_data)} pages. Found {len(all_image_urls)} unique images.")

# Save pages data
with open(os.path.join(DATA_DIR, "scraped_pages.json"), "w", encoding="utf-8") as f:
    json.dump(all_pages_data, f, ensure_ascii=False, indent=2)

# Save images list
with open(os.path.join(DATA_DIR, "image_urls.json"), "w", encoding="utf-8") as f:
    json.dump(list(all_image_urls), f, ensure_ascii=False, indent=2)

print("Saved scraped_pages.json and image_urls.json")
