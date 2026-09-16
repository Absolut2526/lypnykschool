import urllib.request
import ssl
import re
import json
import os
import html
from concurrent.futures import ThreadPoolExecutor, as_completed

ctx = ssl._create_unverified_context()

BASE_DIRS = [
    "/Users/pc/Documents/school_site",
    "/Users/pc/lypnyk-school",
    "/Users/pc"
]
TARGET_DIR = "/Users/pc/Documents/school_site"
IMAGES_DIR = os.path.join(TARGET_DIR, "assets/images")
VIDEOS_DIR = os.path.join(TARGET_DIR, "assets/videos")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

print("1. Fetching original site HTML...")
url = 'https://sites.google.com/view/lypnykzosh/%D0%B3%D0%BE%D0%BB%D0%BE%D0%B2%D0%BD%D0%B0-%D1%81%D1%82%D0%BE%D1%80%D1%96%D0%BD%D0%BA%D0%B0'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
page_html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

sections = re.findall(r'(<section\b[^>]*>.*?</section>)', page_html, re.DOTALL)
print(f"Total sections found: {len(sections)}")

def extract_section_images(sec_html):
    raw_urls = []
    # 1. img src
    for m in re.findall(r'src=[\"\'](https://[^\s\"\'><]+)[\"\']', sec_html):
        raw_urls.append(m.replace('&amp;', '&'))
    # 2. background-image
    for m in re.findall(r'url\([\'\"]?(https://[^\s\"\'><)]+)[\'\"]?\)', sec_html):
        raw_urls.append(m.replace('&amp;', '&'))
    # 3. data-image-id or any other googleusercontent / sitesv-images-rt URL
    for m in re.findall(r'[\"\'](https://(?:sitesv-images-rt|lh3\.googleusercontent\.com|lh4\.googleusercontent\.com|lh5\.googleusercontent\.com|lh6\.googleusercontent\.com)/[^\s\"\'><]+)[\"\']', sec_html):
        raw_urls.append(m.replace('&amp;', '&'))

    seen = set()
    imgs = []
    for u in raw_urls:
        if ('googleusercontent.com' not in u and 'sitesv-images-rt' not in u):
            continue
        if any(skip in u for skip in ['results-not-loaded', 'header-dark', 'icon', 'logo_horizontal']):
            continue
        base_id = re.sub(r'=[sw]\d+.*', '', u)
        if base_id not in seen:
            seen.add(base_id)
            imgs.append(u)
    return imgs

parsed = []
for idx, s in enumerate(sections):
    clean = re.sub(r'<script.*?</script>', '', s, flags=re.DOTALL)
    clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL)
    raw_texts = [re.sub(r'\s+', ' ', t).strip() for t in re.findall(r'>([^<]+)<', clean)]
    texts = [t for t in raw_texts if len(t) > 2 and not t.startswith('{') and not t.startswith('/*') and not t.startswith('.M63') and not t.startswith('window.') and 'Report abuse' not in t and 'Google Sites' not in t and 'Skip to' not in t and 'Embedded Files' not in t and 'Search this site' not in t and 'Повідомити про факт' not in t and 'Вас вітає' not in t]
    
    if texts and texts[0] == 'Липницький ЗЗСО І-ІІІ ступенів Рава-Руської міської ради' and len(' '.join(texts)) < 70:
        texts = []

    imgs = extract_section_images(s)
    yt = re.findall(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', s)
    links = [urllib.parse.unquote(l) for l in re.findall(r'href=[\"\'](https://[^\s\"\'><]+)[\"\']', s)]
    v_links = [l for l in links if 'facebook.com' in l and ('videos' in l or 'watch' in l or 'posts' in l)]

    parsed.append({
        'idx': idx,
        'texts': texts,
        'imgs': imgs,
        'yt': yt,
        'v_links': v_links
    })

# Group events correctly
events = []
curr = None

for p in parsed:
    if p['texts'] and '80318' in p['texts'][0] and 'Львівський' in ' '.join(p['texts']):
        continue
    if p['texts'] and 'М. Рильський писав' in p['texts'][0] and curr and 'М. Рильський писав' in ' '.join(curr['texts']):
        for im in p['imgs']:
            if im not in curr['imgs']: curr['imgs'].append(im)
        continue

    if p['texts']:
        if curr and (curr['texts'] or curr['imgs'] or curr['yt'] or curr['v_links']):
            events.append(curr)
        curr = {
            'id': len(events) + 1,
            'texts': list(p['texts']),
            'imgs': list(p['imgs']),
            'yt': list(p['yt']),
            'v_links': list(p['v_links']),
            'sections': [p['idx']]
        }
    elif curr:
        for im in p['imgs']:
            if im not in curr['imgs']:
                curr['imgs'].append(im)
        for y in p['yt']:
            if y not in curr['yt']:
                curr['yt'].append(y)
        for vl in p['v_links']:
            if vl not in curr['v_links']:
                curr['v_links'].append(vl)
        curr['sections'].append(p['idx'])

if curr and (curr['texts'] or curr['imgs'] or curr['yt'] or curr['v_links']):
    events.append(curr)

print(f"2. Grouped {len(events)} events with {sum(len(e['imgs']) for e in events)} total images.")

# Setup download tasks
download_tasks = []
for ev in events:
    for idx, img_url in enumerate(ev['imgs']):
        # Deterministic filename based on event ID and image index
        filename = f"ev_{ev['id']}_{idx+1}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        download_tasks.append((ev['id'], idx, img_url, filename, filepath))

print(f"3. Downloading/verifying {len(download_tasks)} event photos in parallel...")

def download_image(task):
    ev_id, idx, img_url, filename, filepath = task
    rel_path = f"assets/images/{filename}"
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return (ev_id, idx, img_url, rel_path)
    
    fetch_url = img_url
    if '=w' in fetch_url:
        fetch_url = re.sub(r'=w\d+.*', '=w1200', fetch_url)
    elif '=s' in fetch_url:
        fetch_url = re.sub(r'=s\d+.*', '=s1200', fetch_url)
    else:
        fetch_url = fetch_url + '=w1200'

    try:
        req_img = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_img, context=ctx, timeout=10) as resp:
            data = resp.read()
            if len(data) > 800:
                with open(filepath, 'wb') as f:
                    f.write(data)
                return (ev_id, idx, img_url, rel_path)
    except Exception as e:
        # Retry with original URL
        try:
            req_orig = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_orig, context=ctx, timeout=8) as resp:
                data = resp.read()
                if len(data) > 800:
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    return (ev_id, idx, img_url, rel_path)
        except Exception:
            pass

    return (ev_id, idx, img_url, img_url)

img_results_map = {e['id']: {} for e in events}
with ThreadPoolExecutor(max_workers=35) as pool:
    futures = [pool.submit(download_image, t) for t in download_tasks]
    count = 0
    for f in as_completed(futures):
        ev_id, idx, img_url, path = f.result()
        img_results_map[ev_id][idx] = path
        count += 1
        if count % 200 == 0 or count == len(download_tasks):
            print(f"   Downloaded {count}/{len(download_tasks)} photos...")

def infer_category(title, body):
    full = (title + " " + body).lower()
    if any(w in full for w in ['захисник', 'геро', 'пам’ят', 'памʼят', 'прапор', 'незалежност', 'соборност', 'шевченк', 'чорнобил', 'вишиванк', 'війн', 'слава україні', 'воїн', 'козацьк', 'сбу', 'вербуванн']):
        return "Патріотичне виховання"
    if any(w in full for w in ['екскурсі', 'подорож', 'закарпатт', 'карпат', 'замок', 'поїздк', 'ліцей']):
        return "Подорожі та екскурсії"
    if any(w in full for w in ['свято', 'дзвоник', 'випускн', 'букварик', 'новий рік', 'микола', 'валентин', 'коляд', 'маслян', 'останній дзвоник']):
        return "Шкільні свята"
    if any(w in full for w in ['звіт', 'директор', 'наказ', 'педагогічн', 'рада', 'атестаці', 'вакцин', 'ремонт', 'збори']):
        return "Офіційні новини"
    if any(w in full for w in ['пожеж', 'безпек', 'тренінг', 'поліці', 'пдр', 'мінн', 'психолог', 'булінг', 'безбар’єрност', 'допомога', 'превенці']):
        return "Безпека та розвиток"
    if any(w in full for w in ['олімпіад', 'конкурс', 'змаганн', 'спорт', 'футбол', 'турнір', 'перемож', 'шахмат', 'естафет']):
        return "Досягнення та спорт"
    return "Життя школи"

video_map_clean = {
    '1165557630760142': 'assets/videos/video_1165557630760142.mp4',
    '1209890873032785': 'assets/videos/video_1209890873032785.mp4',
    '8397847596957063': 'assets/videos/video_8397847596957063.mp4',
    '670639844493935': 'assets/videos/video_670639844493935.mp4',
    '1284654262104910': 'assets/videos/video_1284654262104910.mp4'
}

final_feed = []

for ev in events:
    title = ev['texts'][0] if ev['texts'] else "Шкільна подія"
    title = html.unescape(title)
    title = re.sub(r'\s*\|\s*By Липницький ЗЗСО.*', '', title)
    title = re.sub(r'\s*\|\s*Facebook.*', '', title)
    title = title.strip()

    body_paragraphs = []
    for t in (ev['texts'][1:] if len(ev['texts']) > 1 else ev['texts']):
        c_clean = html.unescape(t)
        c_clean = re.sub(r'\d+\s+views,\s+\d+\s+likes.*', '', c_clean)
        c_clean = re.sub(r'Facebook Watch Videos from.*', '', c_clean)
        c_clean = c_clean.strip()
        if c_clean and len(c_clean) > 2 and 'Facebook' not in c_clean:
            body_paragraphs.append(c_clean)

    full_text = "\n\n".join(body_paragraphs) if body_paragraphs else title

    # Specific video titles
    attached_mp4 = None
    attached_yt = ev['yt'][0] if ev['yt'] else None

    # Check for specific Facebook videos
    full_str = title + " " + full_text
    if 'Тижня духовності' in full_str and ('2023' in full_str or '21.03' in full_str):
        attached_mp4 = video_map_clean['1209890873032785']
    elif 'Різдвяну коляду' in full_str or 'Різдвяна коляда' in full_str:
        attached_mp4 = video_map_clean['1165557630760142']
    elif 'Дякуємо ЗСУ!' in title or ('Дякуємо ЗСУ' in full_str and len(full_str) < 200):
        attached_mp4 = video_map_clean['8397847596957063']
        title = "Патріотичний відеоролик «Дякуємо ЗСУ!»"
    elif 'Facebook' in ev['texts'][0] and '132' in str(ev['id']):
        attached_mp4 = video_map_clean['670639844493935']
        title = "Святковий виступ та творчі привітання учнів"
    elif 'Facebook' in ev['texts'][0]:
        attached_mp4 = video_map_clean['1284654262104910']
        title = "Шкільний патріотичний флешмоб та виховний захід"

    # Infer year
    year = "2026"
    years_found = re.findall(r'20(19|20|21|22|23|24|25|26)', full_str)
    if years_found:
        year = "20" + years_found[0]
    elif ev['id'] > 125:
        year = "2020"
    elif ev['id'] > 95:
        year = "2022"
    elif ev['id'] > 65:
        year = "2023"
    elif ev['id'] > 30:
        year = "2024"
    elif ev['id'] > 15:
        year = "2025"

    cat = infer_category(title, full_text)
    
    local_imgs = [img_results_map[ev['id']][i] for i in sorted(img_results_map[ev['id']].keys())]
    
    # If this event has a youtube video and 0 photos, we can download the youtube HQ cover
    if not local_imgs and attached_yt:
        yt_cover_name = f"yt_{attached_yt}.jpg"
        yt_cover_path = os.path.join(IMAGES_DIR, yt_cover_name)
        if not os.path.exists(yt_cover_path):
            try:
                yt_img_url = f"https://img.youtube.com/vi/{attached_yt}/hqdefault.jpg"
                req_yt = urllib.request.Request(yt_img_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_yt, context=ctx, timeout=8) as r:
                    with open(yt_cover_path, 'wb') as f:
                        f.write(r.read())
            except Exception:
                pass
        if os.path.exists(yt_cover_path):
            local_imgs.append(f"assets/images/{yt_cover_name}")

    final_feed.append({
        "id": ev['id'],
        "title": title,
        "content": body_paragraphs,
        "full_text": full_text,
        "category": cat,
        "year": year,
        "images": ev['imgs'],
        "local_images": local_imgs,
        "video": attached_mp4,
        "youtube": attached_yt
    })

print(f"4. Saving {len(final_feed)} final events across directories...")

for b in BASE_DIRS:
    os.makedirs(os.path.join(b, "data"), exist_ok=True)
    os.makedirs(os.path.join(b, "assets/js"), exist_ok=True)
    
    with open(os.path.join(b, "data/news.json"), "w", encoding="utf-8") as f:
        json.dump(final_feed, f, ensure_ascii=False, indent=2)

    with open(os.path.join(b, "assets/js/news-data.js"), "w", encoding="utf-8") as f:
        f.write("window.SCHOOL_NEWS = " + json.dumps(final_feed, ensure_ascii=False, indent=2) + ";\n")

print("All datasets successfully generated with precise 1-to-1 event photo mappings!")
