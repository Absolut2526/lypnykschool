#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Admin Bot for Lypnyk School Website
Allows administrators to manage news, upload photos/videos, add documents, 
delete posts, and receive feedback messages directly from Telegram.
Automatically syncs all changes with Git and pushes to GitHub.
"""

import os
import sys
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
ADMIN_SECRET = "lypnyk2026"  # Password for authorization

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# User session state storage
USER_STATES = {}

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
    # If no admins configured yet, anyone who knows the bot or secret can become admin
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
    # Save to data/news.json
    with open(NEWS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    
    # Save to assets/js/news-data.js
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
            [{"text": "🗑 Видалити новину"}, {"text": "📊 Статистика сайту"}],
            [{"text": "🌐 Посилання на сайт"}]
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

        if data.startswith("cat:"):
            category = data.split(":", 1)[1]
            state["category"] = category
            state["step"] = "WAITING_TEXT"
            USER_STATES[user_id] = state
            
            send_message(chat_id, f"✅ Обрано категорію: <b>{category}</b>\n\n📝 Тепер надішліть <b>повний текст новини</b> (або напишіть <code>-</code> якщо текст такий самий як заголовок):")
            return

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

        if data == "publish_now":
            finish_news_creation(user_id, chat_id)
            return

        if data == "cancel_creation":
            USER_STATES.pop(user_id, None)
            send_message(chat_id, "❌ Створення новини скасовано.", reply_markup=get_main_keyboard())
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
            "• 📄 Додавати офіційні накази та документи\n"
            "• 🗑 Видаляти застарілі новини\n"
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
        USER_STATES[user_id] = {"step": "WAITING_DOC_TITLE"}
        send_message(chat_id, "📄 <b>Додавання документа:</b>\nВведіть назву документа (наприклад: <i>Наказ про зарахування до 1 класу 2026</i>):")
        return

    if text in ["🗑 Видалити новину", "/delete_post"]:
        show_delete_menu(chat_id)
        return

    if text in ["📊 Статистика сайту", "/status"]:
        news = load_news()
        docs = load_docs()
        total_images = len([f for f in os.listdir(IMAGES_DIR) if f.endswith(('.jpg', '.png', '.jpeg'))])
        stat_text = (
            "📊 <b>Статистика сайту Липницького ЗЗСО:</b>\n\n"
            f"• Опублікованих подій: <b>{len(news)}</b>\n"
            f"• Локальних світлин: <b>{total_images}</b>\n"
            f"• Офіційних документів: <b>{len(docs)}</b>\n"
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

    if current_step in ["WAITING_PHOTOS", "QUICK_PHOTO_UPLOAD"]:
        # Check if photo was sent
        if "photo" in msg:
            # Highest resolution photo
            photo = msg["photo"][-1]
            file_id = photo["file_id"]
            state.setdefault("photos", []).append(file_id)
            USER_STATES[user_id] = state
            count = len(state["photos"])
            send_message(chat_id, f"✅ Отримано світлину #{count}! Можете надіслати ще або опублікувати.",
                         reply_markup={"inline_keyboard": [[{"text": "🚀 Опублікувати на сайті", "callback_data": "publish_now"}], [{"text": "❌ Скасувати", "callback_data": "cancel_creation"}]]})
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
        USER_STATES[user_id] = state
        send_message(chat_id, f"📄 Документ: <b>{text}</b>\n\nТепер надішліть <b>текст документа</b> або прикріпіть <b>файл (PDF / DOCX)</b>:")
        return

    if current_step == "WAITING_DOC_CONTENT":
        doc_title = state.get("doc_title")
        slug = doc_title.lower().replace(" ", "-").replace("«", "").replace("»", "").replace("\"", "")
        docs = load_docs()

        doc_body = [text] if text else ["Офіційний документ закладу."]
        doc_links = []

        if "document" in msg:
            doc_file = msg["document"]
            filename = doc_file.get("file_name", f"doc_{int(time.time())}.pdf")
            dest_path = os.path.join(DOCS_DIR, filename)
            download_file(doc_file["file_id"], dest_path)
            doc_links.append(f"assets/docs/{filename}")
            doc_body.append(f"Завантажений файл: {filename}")

        docs[slug] = {
            "title": doc_title,
            "body": doc_body,
            "links": doc_links
        }
        save_docs(docs)
        git_commit_and_push(f"Add document '{doc_title}' via Telegram Bot")
        USER_STATES.pop(user_id, None)
        send_message(chat_id, f"✅ Документ <b>«{doc_title}»</b> успішно додано до бази сайту та опубліковано!", reply_markup=get_main_keyboard())
        return

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

    # Insert at the beginning of the news feed
    news.insert(0, new_item)
    save_news(news)

    # Sync to git
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
    # Show last 6 news
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
