import telebot
import requests
import threading
import time
from datetime import datetime

BOT_TOKEN = '7942960582:AAETZ5KvUiw9_SBoqocKGxqGt8SYbo00D70'
API_BASE = 'https://email-six-pearl.vercel.app'

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
sessions = {}
last_msgs = {}

def api_post(path, payload=None):
    r = requests.post(f"{API_BASE}{path}", json=payload or {})
    return r.json()

def api_get(path):
    r = requests.get(f"{API_BASE}{path}")
    return r.json()

def api_delete(path):
    r = requests.delete(f"{API_BASE}{path}")
    return r.text

@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    help_text = (
        "📌 *Temp Mail Bot Commands*\n\n"
        "/getmail `[provider]` – Create a temp email (optional: mail.tm, dropmail.me, etc)\n"
        "/messages – Check your current inbox\n"
        "/deletesession – Delete the active session\n"
        "/providers – List supported email providers\n"
        "/help – Show this help message"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['providers'])
def list_providers(message):
    try:
        data = api_get("/providers")
        if not data:
            bot.reply_to(message, "⚠️ Could not fetch providers.")
            return
        providers = "\n".join(f"• `{p}`" for p in data)
        bot.reply_to(message, f"📮 *Available Providers:*\n{providers}")
    except:
        bot.reply_to(message, "❌ Error getting providers.")

@bot.message_handler(commands=['getmail'])
def get_mail(message):
    user_id = message.from_user.id
    parts = message.text.split()
    provider = parts[1] if len(parts) > 1 else None
    payload = {"provider": provider} if provider else {}
    try:
        session = api_post("/gen", payload)
        sessions[user_id] = session
        last_msgs[user_id] = set()
        email = session["email_address"]
        prov = session["provider"]
        bot.reply_to(message, f"📧 `{email}`\n🔗 `{prov}`")
    except:
        bot.reply_to(message, "❌ Error generating temp mail.")

@bot.message_handler(commands=['messages'])
def check_messages(message):
    user_id = message.from_user.id
    if user_id not in sessions:
        bot.reply_to(message, "❌ No active session. Use /getmail first.")
        return
    try:
        sid = sessions[user_id]["api_session_id"]
        inbox = api_get(f"/sessions/{sid}/messages")
        if not inbox or not isinstance(inbox, list):
            bot.reply_to(message, "📭 No messages.")
            return
        found = False
        for msg in inbox:
            if not isinstance(msg, dict):
                continue
            f = msg.get("from", "Unknown")
            s = msg.get("subject", "(No Subject)")
            bot.send_message(user_id, f"📨 `{f}`\n📝 `{s}`")
            found = True
        if not found:
            bot.send_message(user_id, "📭 Inbox is empty.")
    except Exception as e:
        bot.send_message(user_id, f"❌ Error reading messages:\n{e}")

@bot.message_handler(commands=['deletesession'])
def delete_session(message):
    user_id = message.from_user.id
    if user_id not in sessions:
        bot.reply_to(message, "❌ No session to delete.")
        return
    sid = sessions[user_id]["api_session_id"]
    api_delete(f"/sessions/{sid}")
    del sessions[user_id]
    del last_msgs[user_id]
    bot.reply_to(message, "🗑️ Session deleted.")

def auto_refresh():
    while True:
        for user_id, session in sessions.items():
            sid = session["api_session_id"]
            inbox = api_get(f"/sessions/{sid}/messages")
            seen = last_msgs.get(user_id, set())
            for msg in inbox:
                if not isinstance(msg, dict):
                    continue
                msg_id = msg.get("id")
                if msg_id not in seen:
                    f = msg.get("from", "Unknown")
                    s = msg.get("subject", "(No Subject)")
                    date = msg.get("date", datetime.utcnow().isoformat())
                    bot.send_message(user_id, f"📬 New Mail:\n📨 `{f}`\n📝 `{s}`\n🕒 `{date}`")
                    seen.add(msg_id)
            last_msgs[user_id] = seen
        time.sleep(30)

def start_polling():
    print("✅ Temp Mail Bot running via telebot polling...")
    threading.Thread(target=auto_refresh, daemon=True).start()
    bot.infinity_polling()

if __name__ == "__main__":
    start_polling()
