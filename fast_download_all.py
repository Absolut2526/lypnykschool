import urllib.request
import ssl
import re
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ctx = ssl._create_unverified_context()
BASE_DIRS = [
    "/Users/pc/Documents/school_site",
    "/Users/pc/lypnyk-school",
    "/Users/pc"
]

print("Reading and parsing old site home page...")
url = 'https://sites.google.com/view/lypnykzosh/%D0%B3%D0%BE%D0%BB%D0%BE%D0%B2%D0%BD%D0%B0-%D1%81%D1%82%D0%BE%D1%80%D1%96%D0%BD%D0%BA%D0%B0'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

sections = re.findall(r'<section\b[^>]*>(.*?)</section>', html, re.DOTALL)
print(f"Total sections: {len(sections)}")

all_posts = []
curr_post = None

for idx, s in enumerate(sections):
    clean = re.sub(r'<script.*?</script>', '', s, flags=re.DOTALL)
    clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL)
    
    raw_texts = re.findall(r'>([^<]+)<', clean)
    texts = []
    for t in raw_texts:
        t_clean = t.replace('&nbsp;', ' ').replace('&quot;', '\"').replace('&amp;', '&').replace('&#39;', "'").strip()
        t_clean = re.sub(r'\s+', ' ', t_clean)
        if len(t_clean) > 2 and not t_clean.startswith('{') and not t_clean.startswith('/*') and not t_clean.startswith('.M63') and not t_clean.startswith('window.') and 'Report abuse' not in t_clean and 'Google Sites' not in t_clean and 'Skip to' not in t_clean and 'Embedded Files' not in t_clean and 'Search this site' not in t_clean and 'Вас вітає' not in t_clean and 'Повідомити про факт' not in t_clean:
            texts.append(t_clean)
            
    imgs = re.findall(r'src=[\"\'](https://[^\s\"\'><]+)[\"\']', s)
    imgs = [img.replace('&amp;', '&') for img in imgs if ('googleusercontent.com' in img or 'sitesv-images-rt' in img) and 'results-not-loaded' not in img and 'logo' not in img and 'header-dark' not in img and 'icon' not in img]

    is_new_event = False
    if texts:
        first_t = texts[0]
        if any(marker in first_t for marker in [
            'З нагоди', 'У Липницькому', 'Свято', 'Сьогодні', 'Національний', 'Вишиванка',
            'Батьки та учні', 'День', 'квітня', 'травня', 'червня', 'липня', 'серпня',
            'вересня', 'жовтня', 'листопада', 'грудня', 'січня', 'лютого', 'березня',
            'Учні', 'Вітаємо', 'Щиро', 'Пам’ятаємо', 'Урочисто', 'Відбулося', 'Проведено',
            'Ось і пролунав', 'Дорогі', 'Шановні', 'Відбувся', 'Звіт', 'Благодійний',
            'Світ професій', 'Незабутня подорож', 'З Днем', 'У рамках', 'Вчителі',
            'У нашому закладі', 'Участь у', 'Тиждень', 'Акція', 'Флешмоб', 'Екскурсія',
            'Завершився', 'Стартував', 'Пам’ять', 'Слава Україні', 'Вітання', 'Змагання',
            'Олімпіада', 'Майстер-клас', 'Тренінг', 'Творчий', 'Вшанування'
        ]):
            is_new_event = True
        elif len(texts) >= 1 and len(first_t) > 35 and not curr_post:
            is_new_event = True
        elif len(texts) >= 1 and len(first_t) > 40 and not first_t.startswith('http'):
            is_new_event = True

    if is_new_event:
        if curr_post and (curr_post['texts'] or curr_post['images']):
            all_posts.append(curr_post)
        curr_post = {
            'id': len(all_posts) + 1,
            'texts': texts,
            'images': imgs
        }
    elif curr_post:
        for im in imgs:
            if im not in curr_post['images']:
                curr_post['images'].append(im)
        for t in texts:
            if t not in curr_post['texts']:
                curr_post['texts'].append(t)

if curr_post and (curr_post['texts'] or curr_post['images']):
    all_posts.append(curr_post)

print(f"Extracted {len(all_posts)} total events!")

# Prepare tasks for downloading all images in parallel
download_tasks = []
target_img_dir = "/Users/pc/Documents/school_site/assets/images"
os.makedirs(target_img_dir, exist_ok=True)

for post in all_posts:
    for idx, img_url in enumerate(post['images']):
        filename = f"event_{post['id']}_{idx+1}.jpg"
        filepath = os.path.join(target_img_dir, filename)
        download_tasks.append((post['id'], idx, img_url, filename, filepath))

print(f"Total images to download in parallel: {len(download_tasks)}")

def download_one(task):
    p_id, idx, img_url, filename, filepath = task
    rel_path = f"assets/images/{filename}"
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return (p_id, idx, img_url, rel_path, True)
    
    fetch_url = img_url
    if '=w' in fetch_url:
        fetch_url = re.sub(r'=w\d+.*', '=w1200', fetch_url)
    elif '=s' in fetch_url:
        fetch_url = re.sub(r'=s\d+.*', '=s1200', fetch_url)
    
    try:
        req_img = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_img, context=ctx, timeout=10) as resp:
            data = resp.read()
            if len(data) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(data)
                return (p_id, idx, img_url, rel_path, True)
    except Exception as e:
        pass
    return (p_id, idx, img_url, img_url, False)

post_images_map = {p['id']: {} for p in all_posts}

with ThreadPoolExecutor(max_workers=30) as executor:
    futures = [executor.submit(download_one, t) for t in download_tasks]
    done_count = 0
    for future in as_completed(futures):
        p_id, idx, img_url, final_url, ok = future.result()
        post_images_map[p_id][idx] = final_url
        done_count += 1
        if done_count % 30 == 0 or done_count == len(download_tasks):
            print(f"Progress: {done_count}/{len(download_tasks)} images processed.")

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

# Construct final dataset
final_events = []
for p in all_posts:
    if not p['texts'] and not p['images']:
        continue
    title = p['texts'][0] if p['texts'] else "Подія шкільного життя"
    body = p['texts'][1:] if len(p['texts']) > 1 else p['texts']
    cat = infer_category(title, ' '.join(body))
    
    year = "2026"
    full_str = ' '.join(p['texts'])
    years_found = re.findall(r'20(19|20|21|22|23|24|25|26)', full_str)
    if years_found:
        year = "20" + years_found[0]
    elif p['id'] > 120:
        year = "2020"
    elif p['id'] > 90:
        year = "2022"
    elif p['id'] > 60:
        year = "2023"
    elif p['id'] > 30:
        year = "2024"
    elif p['id'] > 15:
        year = "2025"

    local_imgs = [post_images_map[p['id']][i] for i in sorted(post_images_map[p['id']].keys())]

    final_events.append({
        "id": p['id'],
        "title": title,
        "content": body,
        "full_text": "\n\n".join(body) if body else title,
        "category": cat,
        "year": year,
        "images": p['images'],
        "local_images": local_imgs
    })

print(f"Total final structured events: {len(final_events)}")

# Write into all project destinations
for base in BASE_DIRS:
    os.makedirs(os.path.join(base, "data"), exist_ok=True)
    os.makedirs(os.path.join(base, "assets/js"), exist_ok=True)
    
    with open(os.path.join(base, "data/news.json"), "w", encoding="utf-8") as f:
        json.dump(final_events, f, ensure_ascii=False, indent=2)

    with open(os.path.join(base, "assets/js/news-data.js"), "w", encoding="utf-8") as f:
        f.write("window.SCHOOL_NEWS = " + json.dumps(final_events, ensure_ascii=False, indent=2) + ";\n")

print("All events and photos transferred successfully!")
