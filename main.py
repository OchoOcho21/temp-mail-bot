import asyncio, aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

BOT_TOKEN = '7942960582:AAETZ5KvUiw9_SBoqocKGxqGt8SYbo00D70'
API_BASE = 'https://email-six-pearl.vercel.app'
sessions = {}
last_msgs = {}

async def api_post(path, payload=None):
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API_BASE}{path}", json=payload or {}) as r:
            return await r.json()

async def api_get(path):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{API_BASE}{path}") as r:
            return await r.json()

async def api_delete(path):
    async with aiohttp.ClientSession() as s:
        async with s.delete(f"{API_BASE}{path}") as r:
            return await r.text()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📌 *Temp Mail Bot Commands*\n\n"
        "/getmail `[provider]` – Create a temp email (optional: mail.tm, dropmail.me, etc)\n"
        "/messages – Check current inbox messages\n"
        "/deletesession – Delete the active session\n"
        "/providers – List supported email providers\n"
        "/help – Show this help message"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def providers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await api_get("/providers")
    if not data:
        await update.message.reply_text("⚠️ Could not fetch providers.")
        return
    provider_list = "\n".join(f"• `{p}`" for p in data)
    await update.message.reply_text(f"📮 *Available Providers:*\n{provider_list}", parse_mode="Markdown")

async def getmail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    provider = args[0] if args else None
    payload = {"provider": provider} if provider else {}
    session = await api_post("/gen", payload)
    sessions[user_id] = session
    last_msgs[user_id] = set()
    email = session["email_address"]
    prov = session["provider"]
    await update.message.reply_text(f"📧 `{email}`\n🔗 `{prov}`", parse_mode="Markdown")

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in sessions:
        await update.message.reply_text("No active session. Use /getmail first.")
        return
    sid = sessions[user_id]["api_session_id"]
    inbox = await api_get(f"/sessions/{sid}/messages")
    if not inbox:
        await update.message.reply_text("📭 No messages.")
        return
    for msg in inbox:
        f = msg.get("from", "Unknown")
        s = msg.get("subject", "(No Subject)")
        await update.message.reply_text(f"📨 `{f}`\n📝 `{s}`", parse_mode="Markdown")

async def deletesession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in sessions:
        await update.message.reply_text("No session to delete.")
        return
    sid = sessions[user_id]["api_session_id"]
    await api_delete(f"/sessions/{sid}")
    del sessions[user_id]
    del last_msgs[user_id]
    await update.message.reply_text("🗑️ Session deleted.")

async def auto_refresh(app):
    while True:
        for user_id, session in sessions.items():
            sid = session["api_session_id"]
            inbox = await api_get(f"/sessions/{sid}/messages")
            seen = last_msgs.get(user_id, set())
            for msg in inbox:
                msg_id = msg.get("id")
                if msg_id not in seen:
                    f = msg.get("from", "Unknown")
                    s = msg.get("subject", "(No Subject)")
                    date = msg.get("date", datetime.utcnow().isoformat())
                    await app.bot.send_message(chat_id=user_id, text=f"📬 New Mail:\n📨 `{f}`\n📝 `{s}`\n🕒 `{date}`", parse_mode="Markdown")
                    seen.add(msg_id)
            last_msgs[user_id] = seen
        await asyncio.sleep(30)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("getmail", getmail))
    app.add_handler(CommandHandler("messages", messages))
    app.add_handler(CommandHandler("deletesession", deletesession))
    app.add_handler(CommandHandler("providers", providers))
    asyncio.create_task(auto_refresh(app))
    print("✅ Temp Mail Bot started with inbox auto-refresh.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
