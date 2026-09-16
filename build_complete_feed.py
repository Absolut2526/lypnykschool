import urllib.request
import ssl
import re
import json
import os
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

print("Fetching full home page HTML...")
url = 'https://sites.google.com/view/lypnykzosh/%D0%B3%D0%BE%D0%BB%D0%BE%D0%B2%D0%BD%D0%B0-%D1%81%D1%82%D0%BE%D1%80%D1%96%D0%BD%D0%BA%D0%B0'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

sections = re.findall(r'<section\b[^>]*>(.*?)</section>', html, re.DOTALL)
print(f"Total sections found: {len(sections)}")

events = []
current_event = None

for idx, s in enumerate(sections):
    clean = re.sub(r'<script.*?</script>', '', s, flags=re.DOTALL)
    clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL)
    
    # Extract visible texts
    raw_texts = [re.sub(r'\s+', ' ', t).strip() for t in re.findall(r'>([^<]+)<', clean)]
    texts = [t for t in raw_texts if len(t) > 2 and not t.startswith('{') and not t.startswith('/*') and not t.startswith('.M63') and not t.startswith('window.') and 'Report abuse' not in t and 'Google Sites' not in t and 'Skip to' not in t and 'Embedded Files' not in t and 'Search this site' not in t and 'Вас вітає' not in t and 'Повідомити про факт' not in t]
    
    # Extract images
    imgs = [img.replace('&amp;', '&') for img in re.findall(r'src=[\"\'](https://[^\s\"\'><]+)[\"\']', s) if ('googleusercontent.com' in img or 'sitesv-images-rt' in img) and 'results-not-loaded' not in img and 'logo' not in img and 'header-dark' not in img and 'icon' not in img]

    # Extract video links
    links = [urllib.parse.unquote(l) for l in re.findall(r'href=[\"\'](https://[^\s\"\'><]+)[\"\']', s)]
    v_links = [l for l in links if 'facebook.com' in l and 'videos' in l]

    if texts:
        # If this text is a real story (not dummy header)
        first_t = texts[0]
        if first_t == 'Липницький ЗЗСО І-ІІІ ступенів Рава-Руської міської ради' and len(' '.join(texts)) < 80:
            continue
        
        # Save previous event
        if current_event and (current_event['texts'] or current_event['images']):
            events.append(current_event)
            
        current_event = {
            'id': len(events) + 1,
            'texts': texts,
            'images': imgs,
            'video_links': v_links
        }
    elif current_event:
        # Append images and videos to current event
        for im in imgs:
            if im not in current_event['images']:
                current_event['images'].append(im)
        for vl in v_links:
            if vl not in current_event['video_links']:
                current_event['video_links'].append(vl)

if current_event and (current_event['texts'] or current_event['images']):
    events.append(current_event)

print(f"Grouped into {len(events)} comprehensive event stories!")
total_images_mapped = sum(len(e['images']) for e in events)
print(f"Total images assigned to events: {total_images_mapped}")

# Download all missing images in parallel
download_tasks = []
for ev in events:
    for idx, img_url in enumerate(ev['images']):
        filename = f"event_{ev['id']}_{idx+1}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        download_tasks.append((ev['id'], idx, img_url, filename, filepath))

print(f"Ensuring all {len(download_tasks)} images are downloaded locally...")

def fetch_image(task):
    ev_id, idx, img_url, filename, filepath = task
    rel_path = f"assets/images/{filename}"
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return (ev_id, idx, img_url, rel_path)
    
    fetch_url = img_url
    if '=w' in fetch_url:
        fetch_url = re.sub(r'=w\d+.*', '=w1200', fetch_url)
    elif '=s' in fetch_url:
        fetch_url = re.sub(r'=s\d+.*', '=s1200', fetch_url)
        
    try:
        req_img = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_img, context=ctx, timeout=8) as resp:
            data = resp.read()
            if len(data) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(data)
                return (ev_id, idx, img_url, rel_path)
    except Exception as e:
        pass
    return (ev_id, idx, img_url, img_url)

img_results_map = {e['id']: {} for e in events}
with ThreadPoolExecutor(max_workers=30) as pool:
    futures = [pool.submit(fetch_image, t) for t in download_tasks]
    done = 0
    for f in as_completed(futures):
        ev_id, idx, img_url, path = f.result()
        img_results_map[ev_id][idx] = path
        done += 1

def infer_category(title, body):
    full = (title + " " + body).lower()
    if any(w in full for w in ['захисник', 'геро', 'пам’ят', 'памʼят', 'прапор', 'незалежност', 'соборност', 'шевченк', 'чорнобил', 'вишиванк', 'війн', 'слава україні', 'воїн', 'козацьк']):
        return "Патріотичне виховання"
    if any(w in full for w in ['екскурсі', 'подорож', 'закарпатт', 'карпат', 'замок', 'поїздк', 'ліцей']):
        return "Подорожі та екскурсії"
    if any(w in full for w in ['свято', 'дзвоник', 'випускн', 'букварик', 'новий рік', 'микола', 'валентин', 'коляд', 'маслян', 'останній дзвоник']):
        return "Шкільні свята"
    if any(w in full for w in ['звіт', 'директор', 'наказ', 'педагогічн', 'рада', 'атестаці']):
        return "Офіційні новини"
    if any(w in full for w in ['пожеж', 'безпек', 'тренінг', 'поліці', 'пдр', 'мінн', 'психолог', 'булінг', 'безбар’єрност', 'допомога']):
        return "Безпека та розвиток"
    if any(w in full for w in ['олімпіад', 'конкурс', 'змаганн', 'спорт', 'футбол', 'турнір', 'перемож', 'шахмат', 'естафет']):
        return "Досягнення та спорт"
    return "Життя школи"

video_map = {
    '1209890873032785': 'assets/videos/video_1209890873032785.mp4',
    '1165557630760142': 'assets/videos/video_1165557630760142.mp4',
    '670639844493935': 'assets/videos/video_670639844493935.mp4',
    '8397847596957063': 'assets/videos/video_8397847596957063.mp4',
    '1284654262104910': 'assets/videos/video_1284654262104910.mp4'
}

final_dataset = []
for ev in events:
    title = ev['texts'][0] if ev['texts'] else "Подія шкільного життя"
    body = ev['texts'][1:] if len(ev['texts']) > 1 else ev['texts']
    cat = infer_category(title, ' '.join(body))
    
    year = "2026"
    full_str = ' '.join(ev['texts'])
    years_found = re.findall(r'20(19|20|21|22|23|24|25|26)', full_str)
    if years_found:
        year = "20" + years_found[0]
    elif ev['id'] > 120:
        year = "2020"
    elif ev['id'] > 90:
        year = "2022"
    elif ev['id'] > 60:
        year = "2023"
    elif ev['id'] > 30:
        year = "2024"
    elif ev['id'] > 15:
        year = "2025"

    local_imgs = [img_results_map[ev['id']][i] for i in sorted(img_results_map[ev['id']].keys())]
    
    # Check attached video
    attached_video = None
    for vl in ev.get('video_links', []):
        for vk, vp in video_map.items():
            if vk in vl:
                attached_video = vp
                break
        if attached_video:
            break
            
    if not attached_video:
        if 'Тижня духовності' in full_str:
            attached_video = 'assets/videos/video_1209890873032785.mp4'
        elif 'Різдвяну коляду' in full_str:
            attached_video = 'assets/videos/video_1165557630760142.mp4'
        elif 'Дякуємо ЗСУ' in full_str:
            attached_video = 'assets/videos/video_8397847596957063.mp4'

    final_dataset.append({
        "id": ev['id'],
        "title": title,
        "content": body,
        "full_text": "\n\n".join(body) if body else title,
        "category": cat,
        "year": year,
        "images": ev['images'],
        "local_images": local_imgs,
        "video": attached_video
    })

print(f"Final structured events count: {len(final_dataset)}")

for b in BASE_DIRS:
    os.makedirs(os.path.join(b, "data"), exist_ok=True)
    os.makedirs(os.path.join(b, "assets/js"), exist_ok=True)
    os.makedirs(os.path.join(b, "assets/images"), exist_ok=True)
    os.makedirs(os.path.join(b, "assets/videos"), exist_ok=True)

    with open(os.path.join(b, "data/news.json"), "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    with open(os.path.join(b, "assets/js/news-data.js"), "w", encoding="utf-8") as f:
        f.write("window.SCHOOL_NEWS = " + json.dumps(final_dataset, ensure_ascii=False, indent=2) + ";\n")

print("All datasets updated successfully!")
