import urllib.request
import ssl
import re
import os
import json
import hashlib
import time

ctx = ssl._create_unverified_context()
DATA_DIR = "/Users/pc/lypnyk-school/data"
IMAGES_DIR = "/Users/pc/lypnyk-school/assets/images"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "scraped_pages.json"), "r", encoding="utf-8") as f:
    scraped_pages = json.load(f)

# Step 1: Parse home page news
url = 'https://sites.google.com/view/lypnykzosh/%D0%B3%D0%BE%D0%BB%D0%BE%D0%B2%D0%BD%D0%B0-%D1%81%D1%82%D0%BE%D1%80%D1%96%D0%BD%D0%BA%D0%B0'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

sections = re.findall(r'<section\b[^>]*>(.*?)</section>', html, re.DOTALL)

posts = []
current_post = None

for i, s in enumerate(sections):
    clean = re.sub(r'<script.*?</script>', '', s, flags=re.DOTALL)
    clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL)
    texts = [re.sub(r'\s+', ' ', t).strip() for t in re.findall(r'>([^<]+)<', clean)]
    texts = [t for t in texts if t and len(t) > 2 and not t.startswith('{') and not t.startswith('/*') and 'Google' not in t and 'Report abuse' not in t]
    
    imgs = re.findall(r'src=[\"\'](https://[^\s\"\'><]+)[\"\']', s)
    imgs = [img.replace('&amp;', '&') for img in imgs if 'googleusercontent' in img or 'sitesv-images-rt' in img]
    imgs = [img for img in imgs if 'results-not-loaded' not in img and 'logo' not in img]

    # Links
    links = re.findall(r'href=[\"\'](https://[^\s\"\'><]+)[\"\']', s)
    links = [l for l in links if 'lypnykzosh' not in l or 'facebook' in l]

    text_content = ' '.join(texts)
    has_story_text = False
    if any(k in text_content for k in ['З нагоди', 'У Липницькому', 'Свято', 'Сьогодні', 'Національний', 'Вишиванка', 'Батьки', 'День', 'квітня', 'травня', 'червня', 'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня', 'січня', 'лютого', 'березня', 'Учні', 'Вітаємо', 'Щиро', 'Пам’ятаємо', 'Урочисто', 'Відбулося', 'Проведено', 'Ось і пролунав', 'Дорогі', 'Шановні', 'Звіт', 'Благодійний']):
        has_story_text = True
    elif len(texts) > 0 and len(text_content) > 30 and not any(k in text_content for k in ['Вас вітає', 'Повідомити про факт', 'Skip to', 'Embedded Files']):
        has_story_text = True

    if has_story_text:
        if current_post and (current_post['texts'] or current_post['images']):
            posts.append(current_post)
        current_post = {
            'id': len(posts) + 1,
            'texts': texts,
            'images': imgs,
            'links': links
        }
    elif current_post:
        if imgs:
            for img in imgs:
                if img not in current_post['images']:
                    current_post['images'].append(img)
        if texts and not any(k in text_content for k in ['Skip to', 'Embedded Files']):
            for t in texts:
                if t not in current_post['texts']:
                    current_post['texts'].append(t)
        if links:
            for l in links:
                if l not in current_post['links']:
                    current_post['links'].append(l)

if current_post and (current_post['texts'] or current_post['images']):
    posts.append(current_post)

print(f"Total news stories extracted: {len(posts)}")

# Categorize and tag news
def infer_category(title, body):
    full = (title + " " + body).lower()
    if any(w in full for w in ['захисник', 'геро', 'пам’ят', 'памʼят', 'прапор', 'незалежност', 'соборност', 'шевченк', 'чорнобил', 'вишиванк', 'війн', 'слава україні', 'воїн']):
        return "Патріотичне виховання"
    if any(w in full for w in ['екскурсі', 'подорож', 'закарпатт', 'карпат', 'замок', 'поїздк']):
        return "Подорожі та екскурсії"
    if any(w in full for w in ['свято', 'дзвоник', 'випускн', 'букварик', 'новий рік', 'микола', 'валентин', 'коляд']):
        return "Шкільні свята"
    if any(w in full for w in ['звіт', 'директор', 'наказ', 'педагогічн', 'рада', 'атестаці']):
        return "Офіційні новини"
    if any(w in full for w in ['пожеж', 'безпек', 'тренінг', 'поліці', 'пдр', 'мінн', 'психолог', 'булінг', 'безбар’єрност']):
        return "Безпека та розвиток"
    if any(w in full for w in ['олімпіад', 'конкурс', 'змаганн', 'спорт', 'футбол', 'турнір', 'перемож']):
        return "Досягнення та спорт"
    return "Життя школи"

refined_news = []
for p in posts:
    if not p['texts'] and not p['images']:
        continue
    title = p['texts'][0] if p['texts'] else "Подія шкільного життя"
    body = p['texts'][1:] if len(p['texts']) > 1 else p['texts']
    category = infer_category(title, ' '.join(body))
    
    # Try to extract year / date mention
    year = "2026"
    full_str = ' '.join(p['texts'])
    years_found = re.findall(r'20(19|20|21|22|23|24|25|26)', full_str)
    if years_found:
        year = "20" + years_found[0]
    
    refined_news.append({
        "id": p['id'],
        "title": title,
        "content": body,
        "full_text": "\n\n".join(body) if body else title,
        "category": category,
        "year": year,
        "images": p['images'],
        "links": p['links'],
        "featured": len(refined_news) < 6
    })

# Save news data
with open(os.path.join(DATA_DIR, "news.json"), "w", encoding="utf-8") as f:
    json.dump(refined_news, f, ensure_ascii=False, indent=2)

print(f"Saved {len(refined_news)} news items into data/news.json")

# Step 2: Download the top 60 key images for local offline high speed rendering
print("Downloading top key images for local fast caching...")
img_map = {}
downloaded_count = 0

for item in refined_news[:45]:
    for idx, img_url in enumerate(item['images'][:4]):
        if downloaded_count >= 60:
            break
        try:
            # Create a clean filename
            img_id = f"news_{item['id']}_{idx+1}.jpg"
            img_path = os.path.join(IMAGES_DIR, img_id)
            if not os.path.exists(img_path):
                # Set width to 1200 for good quality
                fetch_url = img_url
                if '=w' in fetch_url:
                    fetch_url = re.sub(r'=w\d+.*', '=w1200', fetch_url)
                elif '=s' in fetch_url:
                    fetch_url = re.sub(r'=s\d+.*', '=s1200', fetch_url)
                
                req = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    data = resp.read()
                    if len(data) > 1000:
                        with open(img_path, 'wb') as img_f:
                            img_f.write(data)
                        img_map[img_url] = f"assets/images/{img_id}"
                        downloaded_count += 1
                        print(f"Downloaded [{downloaded_count}]: {img_id} ({len(data)//1024} KB)")
            else:
                img_map[img_url] = f"assets/images/{img_id}"
        except Exception as e:
            # Fallback to direct URL if download fails
            img_map[img_url] = img_url

with open(os.path.join(DATA_DIR, "image_map.json"), "w", encoding="utf-8") as f:
    json.dump(img_map, f, ensure_ascii=False, indent=2)

print(f"Downloaded {downloaded_count} images successfully. Image map saved.")

# Step 3: Parse and organize all site sections into structured catalog
site_catalog = {
    "about": {
        "title": "Про школу",
        "description": "Липницький заклад загальної середньої освіти І-ІІІ ступенів Рава-Руської міської ради Львівського району Львівської області",
        "history": "Липницький заклад загальної середньої освіти має багату історію та усталені педагогічні традиції. Заклад забезпечує здобуття якісної повної загальної середньої освіти для учнів 1-11 класів.",
        "leadership": [
            {
                "name": "Гоцій Олександра Іванівна",
                "role": "Директор закладу освіти",
                "bio": "Очолює Липницький ЗЗСО І-ІІІ ступенів, забезпечує стратегічний розвиток закладу та сучасну освітню безпеку."
            },
            {
                "name": "Сухович Ярослав Романович",
                "role": "Почесний багаторічний керівник закладу",
                "bio": "Впродовж багатьох років очолював навчальний заклад, заклав міцний фундамент шкільних традицій."
            }
        ],
        "values": [
            {"title": "Якісна освіта", "desc": "Впровадження стандартів НУШ, розвиток критичного мислення та академічної доброчесності."},
            {"title": "Патріотизм та цінності", "desc": "Виховання свідомих громадян України з глибокою повагою до національної історії."},
            {"title": "Безпека та турбота", "desc": "Безбар'єрне, комфортне і психологічно безпечне середовище для кожної дитини."},
            {"title": "Інновації", "desc": "Сучасні цифрові технології, інтерактивні методи навчання та розвиток творчого потенціалу."}
        ]
    },
    "contacts": {
        "school_name": "Липницький заклад загальної середньої освіти І-ІІІ ступенів",
        "founder": "Рава-Руська міська рада Львівського району Львівської області",
        "address": "вул. Центральна, с. Липник, Львівський район, Львівська область, 80315",
        "email": "lypnyk.zosh@gmail.com",
        
        "work_hours": "Понеділок – П'ятниця: 08:30 – 17:00",
        "facebook": "https://www.facebook.com/lypnykzosh/"
    },
    "documents": [],
    "attestation": [],
    "education_process": [],
    "transparency": []
}

# Process documents and pages from scraped_pages
for p in scraped_pages:
    slug = p['slug']
    title = p['title']
    texts = p['texts']
    doc_links = p['doc_links']
    
    # Transparency docs
    if 'прозорість' in slug or 'фінансово' in slug or 'статут' in slug or 'ліцензія' in slug:
        site_catalog["transparency"].append({
            "slug": slug,
            "title": texts[0] if texts else title,
            "content": texts[1:] if len(texts) > 1 else texts,
            "docs": doc_links
        })
    elif 'атестація' in slug:
        site_catalog["attestation"].append({
            "slug": slug,
            "title": texts[0] if texts else title,
            "content": texts[1:] if len(texts) > 1 else texts,
            "docs": doc_links
        })
    elif 'навчальний-процес' in slug or 'дистанційне' in slug or 'індивідуальна' in slug:
        site_catalog["education_process"].append({
            "slug": slug,
            "title": texts[0] if texts else title,
            "content": texts[1:] if len(texts) > 1 else texts,
            "docs": doc_links
        })
    
    for dl in doc_links:
        doc_name = texts[0] if texts else title
        site_catalog["documents"].append({
            "title": doc_name,
            "url": dl,
            "category": "Офіційні документи",
            "page_slug": slug
        })

with open(os.path.join(DATA_DIR, "site_catalog.json"), "w", encoding="utf-8") as f:
    json.dump(site_catalog, f, ensure_ascii=False, indent=2)

print("Saved site_catalog.json successfully!")
