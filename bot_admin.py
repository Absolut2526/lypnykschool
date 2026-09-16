#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Admin Bot for Lypnyk School Website
Allows administrators to manage news, upload photos/videos, add and delete documents from specific pages/sections,
delete posts, and receive feedback messages directly from Telegram.
Automatically syncs all changes with Git and pushes to GitHub.
"""

import os
import sys
import re
import json
import time
import subprocess
import requests
from datetime import datetime

# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8830753806:AAHdpipDs8KoVCCBeoJba4FakrJqabb46MQ")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")
DOCS_DIR = os.path.join(BASE_DIR, "assets", "docs")
VIDEOS_DIR = os.path.join(BASE_DIR, "assets", "videos")
CONFIG_FILE = os.path.join(DATA_DIR, "admin_config.json")
NEWS_JSON_FILE = os.path.join(DATA_DIR, "news.json")
NEWS_JS_FILE = os.path.join(BASE_DIR, "assets", "js", "news-data.js")
DOCS_JS_FILE = os.path.join(BASE_DIR, "assets", "js", "documents-data.js")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# User session state storage
USER_STATES = {}
DOC_CACHE = {}  # numeric ID -> slug

# Document Placement Destinations
DOC_DESTINATIONS = {
    "trans_statute": {
        "name": "🏛️ Прозорість: Установчі (Статут / Ліцензія / ВСЗЯО)",
        "file": "transparency.html",
        "target_id": "statute",
        "badge": "Установчий документ"
    },
    "trans_finance": {
        "name": "💰 Прозорість: Фінансова звітність та кошториси",
        "file": "transparency.html",
        "target_id": "finance",
        "badge": "Фінансова звітність"
    },
    "trans_reports": {
        "name": "📋 Прозорість: Звіти директора та Накази",
        "file": "transparency.html",
        "target_id": "reports",
        "badge": "Офіційний наказ/звіт"
    },
    "parents_adm": {
        "name": "👨‍👩‍👧 Батькам: 1 клас, накази та правила",
        "file": "parents.html",
        "target_id": "parent-docs",
        "badge": "Інформація для батьків"
    },
    "attestation": {
        "name": "🎓 Атестація педагогів (графіки / списки)",
        "file": "attestation.html",
        "target_id": "regulations",
        "badge": "Атестація"
    },
    "psychologist": {
        "name": "💙 Психологічна служба та Стоп Булінг",
        "file": "psychologist.html",
        "target_id": "regulations",
        "badge": "Безпека та психологія"
    },
    "education": {
        "name": "📚 Навчальний процес (НУШ / Програми)",
        "file": "education.html",
        "target_id": "curriculum",
        "badge": "Освітній процес"
    }
}

def get_doc_id(slug):
    """Maps a document slug to a compact integer ID for Telegram callback buttons."""
    for k, v in DOC_CACHE.items():
        if v == slug:
            return k
    new_id = len(DOC_CACHE) + 1
    DOC_CACHE[new_id] = slug
    return new_id

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"admin_ids": []}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    cfg = load_config()
    if not cfg.get("admin_ids"):
        return True
    return user_id in cfg.get("admin_ids", [])

def add_admin(user_id):
    cfg = load_config()
    if user_id not in cfg.get("admin_ids", []):
        cfg.setdefault("admin_ids", []).append(user_id)
        save_config(cfg)

def git_commit_and_push(commit_message):
    """Commits all local changes and pushes to origin main."""
    try:
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True, capture_output=True)
        res_commit = subprocess.run(["git", "commit", "-m", commit_message], cwd=BASE_DIR, capture_output=True, text=True)
        print(f"[Git Commit] {res_commit.stdout.strip()}")
        res_push = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True)
        print(f"[Git Push] {res_push.stdout.strip()}")
        return True, "Успішно збережено та синхронізовано з GitHub 🚀"
    except Exception as e:
        print(f"[Git Error] {e}")
        return False, f"Помилка Git: {e}"

def load_news():
    if os.path.exists(NEWS_JSON_FILE):
        with open(NEWS_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_news(news_list):
    with open(NEWS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    
    js_content = "window.SCHOOL_NEWS = " + json.dumps(news_list, ensure_ascii=False, indent=2) + ";\n"
    with open(NEWS_JS_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

def load_docs():
    docs = {}
    if os.path.exists(DOCS_JS_FILE):
        try:
            with open(DOCS_JS_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if "window.SCHOOL_DOCUMENTS =" in content:
                json_str = content.split("window.SCHOOL_DOCUMENTS =", 1)[1].strip().rstrip(";")
                docs = json.loads(json_str)
        except Exception as e:
            print(f"Error loading docs: {e}")
    return docs

def save_docs(docs_dict):
    js_content = "window.SCHOOL_DOCUMENTS = " + json.dumps(docs_dict, ensure_ascii=False, indent=2) + ";\n"
    with open(DOCS_JS_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

def remove_doc_from_html_pages(slug):
    """Finds and removes any .doc-card referencing the slug from all HTML pages."""
    html_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.html')]
    modified = False
    pattern = re.compile(r'<div class="doc-card"[^>]*>(?:(?!<div class="doc-card").)*?openDocModal\([\'"]' + re.escape(slug) + r'[\'"]\).*?</div>\s*', re.DOTALL)
    for fname in html_files:
        fpath = os.path.join(BASE_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            if pattern.search(content):
                new_content = pattern.sub('', content)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                modified = True
                print(f"Removed doc-card for {slug} from {fname}")
        except Exception as e:
            print(f"Error removing card from {fname}: {e}")
    return modified

# Telegram API Helpers
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def download_file(file_id, dest_path):
    try:
        file_info_res = requests.get(f"{API_URL}/getFile?file_id={file_id}", timeout=15).json()
        if not file_info_res.get("ok"):
            return False
        file_path = file_info_res["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        r = requests.get(download_url, timeout=30)
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

# Keyboards
def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "➕ Опублікувати новину"}, {"text": "📄 Додати документ"}],
            [{"text": "🗑 Видалити новину"}, {"text": "🗑 Видалити документ"}],
            [{"text": "📊 Статистика сайту"}, {"text": "🌐 Посилання на сайт"}]
        ],
        "resize_keyboard": True
    }

def get_categories_inline():
    return {
        "inline_keyboard": [
            [{"text": "🇺🇦 Патріотичне виховання", "callback_data": "cat:Патріотичне виховання"}],
            [{"text": "🔔 Шкільні свята", "callback_data": "cat:Шкільні свята"}],
            [{"text": "⛰️ Подорожі та екскурсії", "callback_data": "cat:Подорожі та екскурсії"}],
            [{"text": "📜 Офіційні новини", "callback_data": "cat:Офіційні новини"}],
            [{"text": "🛡️ Безпека та розвиток", "callback_data": "cat:Безпека та розвиток"}],
            [{"text": "🏆 Досягнення та спорт", "callback_data": "cat:Досягнення та спорт"}]
        ]
    }

def get_doc_destinations_inline():
    buttons = []
    for key, info in DOC_DESTINATIONS.items():
        buttons.append([{"text": info["name"], "callback_data": f"docdest:{key}"}])
    buttons.append([{"text": "❌ Скасувати", "callback_data": "cancel_creation"}])
    return {"inline_keyboard": buttons}

def get_delete_doc_categories_inline():
    return {
        "inline_keyboard": [
            [{"text": "🆕 Останні додані документи", "callback_data": "deldoc_filter:recent"}],
            [{"text": "🏛️ Прозорість (Статут / Звіти / Накази)", "callback_data": "deldoc_filter:trans"}],
            [{"text": "👨‍👩‍👧 Батькам (1 клас / Розклад)", "callback_data": "deldoc_filter:parents"}],
            [{"text": "🎓 Атестація педагогів", "callback_data": "deldoc_filter:attest"}],
            [{"text": "💙 Психологічна служба (Булінг)", "callback_data": "deldoc_filter:psych"}],
            [{"text": "📚 Навчальний процес (НУШ)", "callback_data": "deldoc_filter:edu"}],
            [{"text": "🔍 Пошук за назвою документа", "callback_data": "deldoc_filter:search"}],
            [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]
        ]
    }

def insert_doc_into_html(file_name, target_id, doc_title, subtitle, slug):
    """Inserts a new document card into the selected HTML page's grid."""
    file_path = os.path.join(BASE_DIR, file_name)
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        new_card = f'''
        <div class="doc-card">
          <div class="doc-info">
            <div class="doc-icon"><i class="fas fa-file-pdf"></i></div>
            <div>
              <div class="doc-name">{doc_title}</div>
              <span style="font-size: 0.8rem; color: var(--text-muted);">{subtitle}</span>
            </div>
          </div>
          <a href="javascript:void(0)" onclick="openDocModal('{slug}')" class="btn btn-sm btn-secondary">
            <i class="fas fa-external-link-alt"></i> Переглянути
          </a>
        </div>'''

        # Try to find target_id first
        if target_id and f'id="{target_id}"' in html:
            sec_idx = html.find(f'id="{target_id}"')
            grid_idx = html.find('class="doc-card-grid"', sec_idx)
            if grid_idx != -1:
                closing_tag = html.find('>', grid_idx)
                if closing_tag != -1:
                    html = html[:closing_tag+1] + new_card + html[closing_tag+1:]
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    return True

        # Fallback: find any .doc-card-grid
        grid_idx = html.find('class="doc-card-grid"')
        if grid_idx != -1:
            closing_tag = html.find('>', grid_idx)
            if closing_tag != -1:
                html = html[:closing_tag+1] + new_card + html[closing_tag+1:]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return True
    except Exception as e:
        print(f"Error inserting doc into {file_name}: {e}")
    return False

def show_doc_delete_list(chat_id, filter_type=None, search_query=None):
    docs = load_docs()
    if not docs:
        send_message(chat_id, "База документів порожня.")
        return

    # Filter out dummy internal keys
    doc_items = [(slug, data) for slug, data in docs.items() if slug not in ["головна-сторінка"]]

    filtered = []
    if filter_type == "recent":
        filtered = doc_items[-10:]
        filtered.reverse()
    elif filter_type == "trans":
        filtered = [(s, d) for s, d in doc_items if any(k in s for k in ["статут", "ліцензі", "звіт", "кошторис", "наказ", "всзяо", "фінанс", "майн", "структур"])]
    elif filter_type == "parents":
        filtered = [(s, d) for s, d in doc_items if any(k in s for k in ["батьк", "зарахуван", "1-клас", "розклад", "правил", "індивідуал", "екстернат"])]
    elif filter_type == "attest":
        filtered = [(s, d) for s, d in doc_items if any(k in s for k in ["атестац", "кваліфік", "педагог"])]
    elif filter_type == "psych":
        filtered = [(s, d) for s, d in doc_items if any(k in s for k in ["булінг", "цькуван", "психолог", "насильств", "заяв"])]
    elif filter_type == "edu":
        filtered = [(s, d) for s, d in doc_items if any(k in s for k in ["освітн", "нуш", "інклюз", "навчан", "програм"])]
    elif search_query:
        q = search_query.lower().strip()
        filtered = [(s, d) for s, d in doc_items if q in s.lower() or q in d.get("title", "").lower()]
    else:
        filtered = doc_items[:12]

    if not filtered:
        send_message(chat_id, "⚠️ Документів у цій категорії не знайдено.", reply_markup=get_delete_doc_categories_inline())
        return

    buttons = []
    for slug, data in filtered[:10]:
        doc_id = get_doc_id(slug)
        title = data.get("title", slug.replace("-", " "))
        display_title = title[:35] + ("..." if len(title) > 35 else "")
        buttons.append([{"text": f"❌ {display_title}", "callback_data": f"deldoc_ask:{doc_id}"}])

    buttons.append([{"text": "🔙 Назад до вибору розділу", "callback_data": "deldoc_back"}])
    keyboard = {"inline_keyboard": buttons}

    category_titles = {
        "recent": "Останні додані документи",
        "trans": "Розділ «Прозорість»",
        "parents": "Розділ «Батькам»",
        "attest": "Розділ «Атестація»",
        "psych": "Розділ «Психолог / Стоп Булінг»",
        "edu": "Розділ «Навчальний процес»",
    }
    header_name = category_titles.get(filter_type, f"Результати пошуку «{search_query}»" if search_query else "Список документів")
    send_message(chat_id, f"🗑 <b>{header_name}:</b>\nОберіть документ, який бажаєте видалити:", reply_markup=keyboard)

def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb["data"]
        user_id = cb["from"]["id"]
        
        if not is_admin(user_id):
            send_message(chat_id, "⛔ Доступ обмежено.")
            return

        state = USER_STATES.get(user_id, {})

        # News Category Chosen
        if data.startswith("cat:"):
            category = data.split(":", 1)[1]
            state["category"] = category
            state["step"] = "WAITING_TEXT"
            USER_STATES[user_id] = state
            send_message(chat_id, f"✅ Обрано категорію: <b>{category}</b>\n\n📝 Тепер надішліть <b>повний текст новини</b> (або напишіть <code>-</code> якщо текст такий самий як заголовок):")
            return

        # Document Destination Chosen
        if data.startswith("docdest:"):
            dest_key = data.split(":", 1)[1]
            if dest_key not in DOC_DESTINATIONS:
                send_message(chat_id, "⚠️ Невідомий розділ.")
                return
            dest_info = DOC_DESTINATIONS[dest_key]
            state["dest_key"] = dest_key
            state["step"] = "WAITING_DOC_TITLE"
            state["doc_files"] = []
            state["doc_texts"] = []
            USER_STATES[user_id] = state
            
            send_message(chat_id, f"📂 <b>Обрано розділ:</b>\n{dest_info['name']}\n\n📝 <b>Крок 2 із 3:</b> Введіть <b>назву або опис документа</b>\n(Наприклад: <i>Наказ про зарахування до 1 класу 2026</i> або <i>Річний план роботи школи</i>):")
            return

        # News Delete
        if data.startswith("del:"):
            post_id = int(data.split(":", 1)[1])
            news = load_news()
            orig_len = len(news)
            news = [n for n in news if n.get("id") != post_id]
            if len(news) < orig_len:
                save_news(news)
                git_commit_and_push(f"Delete news #{post_id} via Telegram Bot")
                send_message(chat_id, f"🗑 Новину #{post_id} успішно <b>видалено</b> із сайту та репозиторію!", reply_markup=get_main_keyboard())
            else:
                send_message(chat_id, f"⚠️ Новину #{post_id} не знайдено.")
            return

        # Document Deletion Filter
        if data.startswith("deldoc_filter:"):
            ftype = data.split(":", 1)[1]
            if ftype == "search":
                USER_STATES[user_id] = {"step": "WAITING_DOC_SEARCH"}
                send_message(chat_id, "🔍 Введіть <b>ключове слово або назву документа</b> для пошуку (наприклад: <i>статут</i>, <i>наказ</i>, <i>1 клас</i>):")
            else:
                show_doc_delete_list(chat_id, filter_type=ftype)
            return

        if data == "deldoc_back":
            send_message(chat_id, "🗑 <b>Видалення документа:</b> Оберіть розділ або скористайтеся пошуком:", reply_markup=get_delete_doc_categories_inline())
            return

        if data.startswith("deldoc_ask:"):
            doc_id = int(data.split(":", 1)[1])
            slug = DOC_CACHE.get(doc_id)
            docs = load_docs()
            doc_data = docs.get(slug)
            if not doc_data:
                send_message(chat_id, "⚠️ Документ не знайдено або вже видалено.")
                return
            title = doc_data.get("title", slug)
            confirm_kb = {
                "inline_keyboard": [
                    [{"text": "🗑 Так, видалити назавжди", "callback_data": f"deldoc_exec:{doc_id}"}],
                    [{"text": "❌ Ні, скасувати", "callback_data": "deldoc_back"}]
                ]
            }
            send_message(chat_id, f"⚠️ <b>Підтвердження видалення:</b>\n\nВи дійсно бажаєте видалити документ:\n<b>«{title}»</b>\n\nВін буде вилучений із сайту, бази та репозиторію GitHub.", reply_markup=confirm_kb)
            return

        if data.startswith("deldoc_exec:"):
            doc_id = int(data.split(":", 1)[1])
            slug = DOC_CACHE.get(doc_id)
            docs = load_docs()
            if slug in docs:
                doc_title = docs[slug].get("title", slug)
                del docs[slug]
                save_docs(docs)
                remove_doc_from_html_pages(slug)
                git_commit_and_push(f"Delete document '{doc_title[:30]}' via Telegram Bot")
                send_message(chat_id, f"🗑 Документ <b>«{doc_title}»</b> успішно <b>видалено</b> із сайту та репозиторію!", reply_markup=get_main_keyboard())
            else:
                send_message(chat_id, "⚠️ Документ не знайдено.")
            return

        if data == "publish_now":
            finish_news_creation(user_id, chat_id)
            return

        if data == "publish_docs_now":
            finish_document_creation(user_id, chat_id)
            return

        if data == "cancel_creation":
            USER_STATES.pop(user_id, None)
            send_message(chat_id, "❌ Дію скасовано.", reply_markup=get_main_keyboard())
            return

    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "").strip()

    # Automatically register admin on start or command
    add_admin(user_id)

    # Global Cancel
    if text in ["/cancel", "❌ Скасувати", "Скасувати"]:
        USER_STATES.pop(user_id, None)
        send_message(chat_id, "Дію скасовано.", reply_markup=get_main_keyboard())
        return

    # Commands / Menu Buttons
    if text in ["/start", "/admin", "/menu"]:
        USER_STATES.pop(user_id, None)
        welcome_text = (
            "🏫 <b>Панель керування сайтом Липницького ЗЗСО І–ІІ ступенів</b>\n\n"
            "Привіт! Ви маєте права адміністратора. Через цього бота ви можете:\n"
            "• ➕ Публікувати нові події з фото та відео\n"
            "• 📄 Додавати офіційні накази та документи у вибраний розділ сайту\n"
            "• 🗑 Видаляти застарілі новини або документи\n"
            "• 📊 Переглядати актуальну статистику сайту\n"
            "• 📬 Отримувати електронні звернення від батьків та учнів\n\n"
            "Усі зміни автоматично зберігаються на сайті та пушаться на GitHub!"
        )
        send_message(chat_id, welcome_text, reply_markup=get_main_keyboard())
        return

    if text in ["➕ Опублікувати новину", "/new_post"]:
        USER_STATES[user_id] = {"step": "WAITING_TITLE", "photos": []}
        send_message(chat_id, "📝 <b>Крок 1 із 4:</b> Введіть <b>заголовок або назву події</b>:\n(Наприклад: <i>Свято Останнього дзвоника у Липницькому ЗЗСО</i>)")
        return

    if text in ["📄 Додати документ", "/add_doc"]:
        USER_STATES[user_id] = {"step": "CHOOSING_DOC_DEST"}
        send_message(chat_id, "📄 <b>Крок 1 із 3: Оберіть розділ сайту</b>, куди саме додати новий документ(и):", reply_markup=get_doc_destinations_inline())
        return

    if text in ["🗑 Видалити новину", "/delete_post"]:
        show_delete_menu(chat_id)
        return

    if text in ["🗑 Видалити документ", "/delete_doc"]:
        send_message(chat_id, "🗑 <b>Видалення документа:</b> Оберіть категорію або скористайтеся пошуком за назвою:", reply_markup=get_delete_doc_categories_inline())
        return

    if text in ["📊 Статистика сайту", "/status"]:
        news = load_news()
        docs = load_docs()
        total_images = len([f for f in os.listdir(IMAGES_DIR) if f.endswith(('.jpg', '.png', '.jpeg'))])
        total_docs = len([f for f in os.listdir(DOCS_DIR) if not f.startswith('.')])
        stat_text = (
            "📊 <b>Статистика сайту Липницького ЗЗСО:</b>\n\n"
            f"• Опублікованих подій: <b>{len(news)}</b>\n"
            f"• Локальних світлин: <b>{total_images}</b>\n"
            f"• База документів у системі: <b>{len(docs)}</b>\n"
            f"• Завантажених файлів (PDF/Word): <b>{total_docs}</b>\n"
            f"• Репозиторій: <a href='https://github.com/Absolut2526/school_site'>GitHub (main)</a>\n"
            f"• Ступінь школи: <b>1–9 класи (І–ІІ ступенів)</b>"
        )
        send_message(chat_id, stat_text)
        return

    if text in ["🌐 Посилання на сайт", "/link"]:
        send_message(chat_id, "🌐 <b>Посилання на сайт закладу:</b>\n• Репозиторій: https://github.com/Absolut2526/school_site\n• Локальна папка: <code>/Users/pc/Documents/school_site</code>")
        return

    # State Machine Handling
    state = USER_STATES.get(user_id)
    if not state:
        send_message(chat_id, "Оберіть дію з меню нижче 👇", reply_markup=get_main_keyboard())
        return

    current_step = state.get("step")

    # Document Search Step
    if current_step == "WAITING_DOC_SEARCH":
        USER_STATES.pop(user_id, None)
        show_doc_delete_list(chat_id, search_query=text)
        return

    # Flow 1: News Creation
    if current_step == "WAITING_TITLE":
        state["title"] = text
        state["step"] = "WAITING_CATEGORY"
        USER_STATES[user_id] = state
        send_message(chat_id, f"📌 Заголовок: <b>{text}</b>\n\n<b>Крок 2 із 4:</b> Оберіть тематичну категорію:", reply_markup=get_categories_inline())
        return

    if current_step == "WAITING_TEXT":
        body_text = text if text != "-" else state.get("title")
        state["full_text"] = body_text
        state["step"] = "WAITING_PHOTOS"
        USER_STATES[user_id] = state
        send_message(chat_id, "📸 <b>Крок 3 із 4:</b> Тепер надішліть <b>одну або кілька фотографій</b> (або відеоролик).\n\nКоли завершите надсилати світлини, натисніть кнопку нижче:", 
                     reply_markup={"inline_keyboard": [[{"text": "🚀 Завершити та Опублікувати", "callback_data": "publish_now"}], [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]]})
        return

    if current_step == "WAITING_PHOTOS":
        if "photo" in msg:
            photo = msg["photo"][-1]
            file_id = photo["file_id"]
            state.setdefault("photos", []).append(file_id)
            USER_STATES[user_id] = state
            count = len(state["photos"])
            send_message(chat_id, f"✅ Отримано світлину #{count}! Можете надіслати ще або опублікувати.",
                         reply_markup={"inline_keyboard": [[{"text": f"🚀 Опублікувати на сайті ({count} фото)", "callback_data": "publish_now"}], [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]]})
            return

        if "video" in msg:
            video = msg["video"]
            state["video_file_id"] = video["file_id"]
            USER_STATES[user_id] = state
            send_message(chat_id, "🎥 Відео отримано! Натисніть кнопку нижче для публікації.",
                         reply_markup={"inline_keyboard": [[{"text": "🚀 Опублікувати на сайті", "callback_data": "publish_now"}], [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]]})
            return

    # Flow 2: Document Creation
    if current_step == "WAITING_DOC_TITLE":
        state["doc_title"] = text
        state["step"] = "WAITING_DOC_CONTENT"
        state["doc_files"] = []
        state["doc_texts"] = []
        USER_STATES[user_id] = state
        dest_info = DOC_DESTINATIONS.get(state.get("dest_key", ""), {})
        dest_name = dest_info.get("name", "Сайт")
        send_message(chat_id, 
            f"📄 <b>Документ:</b> {text}\n"
            f"📂 <b>Розділ:</b> {dest_name}\n\n"
            "📎 <b>Крок 3 із 3:</b> Надішліть <b>файл(и) документа</b> (PDF, DOCX, XLSX, фотоскан) або напишіть <b>текст</b>.\n\n"
            "💡 Ви можете надіслати <b>декілька файлів підряд</b>!\n"
            "Коли завершите надсилати, натисніть кнопку нижче 👇",
            reply_markup={"inline_keyboard": [
                [{"text": "🚀 Опублікувати на сайті", "callback_data": "publish_docs_now"}],
                [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]
            ]}
        )
        return

    if current_step == "WAITING_DOC_CONTENT":
        if "document" in msg:
            doc_file = msg["document"]
            file_id = doc_file["file_id"]
            orig_name = doc_file.get("file_name", f"doc_{int(time.time())}.pdf")
            state.setdefault("doc_files", []).append({
                "file_id": file_id,
                "file_name": orig_name
            })
            USER_STATES[user_id] = state
            count = len(state["doc_files"])
            send_message(chat_id, 
                f"✅ Отримано документ #{count}: <b>{orig_name}</b>\n\n"
                "Можете надіслати ще файли або опублікувати на сайті:",
                reply_markup={"inline_keyboard": [
                    [{"text": f"🚀 Опублікувати на сайті ({count} файл{'ів' if count > 4 else 'и' if count > 1 else ''})", "callback_data": "publish_docs_now"}],
                    [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]
                ]}
            )
            return

        if "photo" in msg:
            photo = msg["photo"][-1]
            file_id = photo["file_id"]
            orig_name = f"scan_{int(time.time())}.jpg"
            state.setdefault("doc_files", []).append({
                "file_id": file_id,
                "file_name": orig_name
            })
            USER_STATES[user_id] = state
            count = len(state["doc_files"])
            send_message(chat_id, 
                f"✅ Отримано скан/фото #{count}!\n\n"
                "Можете надіслати ще файли або опублікувати на сайті:",
                reply_markup={"inline_keyboard": [
                    [{"text": f"🚀 Опублікувати на сайті ({count} файл{'ів' if count > 4 else 'и' if count > 1 else ''})", "callback_data": "publish_docs_now"}],
                    [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]
                ]}
            )
            return

        if text:
            state.setdefault("doc_texts", []).append(text)
            USER_STATES[user_id] = state
            send_message(chat_id, 
                "📝 Текст додано! Надішліть файл або натисніть «Опублікувати на сайті»:",
                reply_markup={"inline_keyboard": [
                    [{"text": "🚀 Опублікувати на сайті", "callback_data": "publish_docs_now"}],
                    [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]
                ]}
            )
            return

def finish_document_creation(user_id, chat_id):
    state = USER_STATES.get(user_id, {})
    doc_title = state.get("doc_title", "Офіційний документ")
    dest_key = state.get("dest_key", "trans_reports")
    dest_info = DOC_DESTINATIONS.get(dest_key, DOC_DESTINATIONS["trans_reports"])
    doc_files = state.get("doc_files", [])
    doc_texts = state.get("doc_texts", [])

    send_message(chat_id, "⏳ Зберігаю файли та додаю документ у вибраний розділ сайту...")

    # Download files to assets/docs/
    downloaded_links = []
    for item in doc_files:
        raw_name = item["file_name"]
        clean_name = re.sub(r'[^a-zA-Z0-9_\.\-]', '_', raw_name)
        unique_name = f"{int(time.time())}_{clean_name}"
        dest_path = os.path.join(DOCS_DIR, unique_name)
        if download_file(item["file_id"], dest_path):
            downloaded_links.append(f"assets/docs/{unique_name}")

    # Generate slug
    slug = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄґҐ\-]', '-', doc_title.lower()).strip('-')
    if not slug:
        slug = f"doc-{int(time.time())}"

    # Build body
    body_paragraphs = []
    if doc_texts:
        body_paragraphs.extend(doc_texts)
    else:
        body_paragraphs.append(f"Офіційний документ закладу загальної середньої освіти: {doc_title}.")

    if downloaded_links:
        for idx, l in enumerate(downloaded_links):
            body_paragraphs.append(f"Доданий файл #{idx+1}: {os.path.basename(l)}")

    # Update documents-data.js
    docs = load_docs()
    docs[slug] = {
        "title": doc_title,
        "subtitle": dest_info["badge"],
        "body": body_paragraphs,
        "links": downloaded_links
    }
    save_docs(docs)

    # Insert doc card into the target HTML page
    html_file = dest_info["file"]
    target_id = dest_info["target_id"]
    badge_text = dest_info["badge"]
    insert_doc_into_html(html_file, target_id, doc_title, badge_text, slug)

    # Commit and push
    ok, git_msg = git_commit_and_push(f"Add document '{doc_title[:30]}' to {html_file} via Telegram Bot")

    USER_STATES.pop(user_id, None)

    success_text = (
        "🎉 <b>Документ успішно додано на сайт!</b>\n\n"
        f"📄 <b>Назва:</b> {doc_title}\n"
        f"📂 <b>Розділ сайту:</b> {dest_info['name']}\n"
        f"📑 <b>Файлів завантажено:</b> {len(downloaded_links)}\n"
        f"🌐 <b>Сторінка:</b> <code>{html_file}</code>\n\n"
        f"🚀 <i>{git_msg}</i>"
    )
    send_message(chat_id, success_text, reply_markup=get_main_keyboard())

def finish_news_creation(user_id, chat_id):
    state = USER_STATES.get(user_id, {})
    title = state.get("title", "Нова подія школи")
    category = state.get("category", "Офіційні новини")
    full_text = state.get("full_text", title)
    photos = state.get("photos", [])
    video_file_id = state.get("video_file_id")

    send_message(chat_id, "⏳ Зберігаю світлини та генерую оновлення сайту...")

    news = load_news()
    max_id = max([n.get("id", 0) for n in news]) if news else 0
    new_id = max_id + 1
    current_year = str(datetime.now().year)

    local_images = []
    for idx, photo_id in enumerate(photos):
        filename = f"ev_{new_id}_{idx+1}.jpg"
        dest = os.path.join(IMAGES_DIR, filename)
        if download_file(photo_id, dest):
            local_images.append(f"assets/images/{filename}")

    local_video = None
    if video_file_id:
        v_filename = f"video_{new_id}.mp4"
        v_dest = os.path.join(VIDEOS_DIR, v_filename)
        if download_file(video_file_id, v_dest):
            local_video = f"assets/videos/{v_filename}"

    new_item = {
        "id": new_id,
        "title": title,
        "content": [full_text[:200] + "..."] if len(full_text) > 200 else [full_text],
        "full_text": full_text,
        "category": category,
        "year": current_year,
        "images": [],
        "local_images": local_images,
        "video": local_video,
        "youtube": None
    }

    news.insert(0, new_item)
    save_news(news)

    ok, git_msg = git_commit_and_push(f"Add news #{new_id} '{title[:35]}...' via Telegram Bot")

    USER_STATES.pop(user_id, None)

    success_msg = (
        f"🎉 <b>Новину успішно опубліковано!</b>\n\n"
        f"📌 <b>Заголовок:</b> {title}\n"
        f"🏷️ <b>Категорія:</b> {category}\n"
        f"📸 <b>Додано світлин:</b> {len(local_images)}\n"
        f"📅 <b>Рік:</b> {current_year}\n\n"
        f"🌐 <i>{git_msg}</i>"
    )
    send_message(chat_id, success_msg, reply_markup=get_main_keyboard())

def show_delete_menu(chat_id):
    news = load_news()
    if not news:
        send_message(chat_id, "Новини відсутні.")
        return

    buttons = []
    for item in news[:6]:
        item_id = item.get("id")
        title = item.get("title", "")[:35] + "..."
        buttons.append([{"text": f"❌ Видалити #{item_id}: {title}", "callback_data": f"del:{item_id}"}])

    keyboard = {"inline_keyboard": buttons}
    send_message(chat_id, "🗑 <b>Оберіть новину, яку бажаєте видалити:</b>", reply_markup=keyboard)

def main():
    print(f"[*] Starting Lypnyk School Telegram Bot Daemon (@LypnykSchoolBot)...")
    offset = 0
    while True:
        try:
            url = f"{API_URL}/getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=25).json()
            if res.get("ok"):
                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    handle_update(update)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopping bot daemon.")
            break
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
