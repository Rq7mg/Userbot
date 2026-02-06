import os
import asyncio
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================== ENV ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
OWNER_ID = int(os.environ["OWNER_ID"])

# ================== GLOBAL ==================
LOGIN_STEP = {}
TEMP_CLIENT = {}
USERBOTS = {}   # uid -> TelegramClient
STOP_FLAGS = {}

# ================== JSON ==================
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
    with open(file) as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# ================== PREMIUM ==================
def is_premium(uid):
    data = load_json("authorized.json", {"users": []})
    return uid == OWNER_ID or uid in data["users"]

# ================== BOT COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        await update.message.reply_text("❌ Premium değilsin")
        return
    await update.message.reply_text(
        "✅ Userbot sistemi\n\n"
        "/login → hesap bağla\n"
        ".ig .gn .t .stop"
    )

async def pre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        uid = int(context.args[0])
    except:
        await update.message.reply_text("Kullanım: /pre USER_ID")
        return
    data = load_json("authorized.json", {"users": []})
    if uid not in data["users"]:
        data["users"].append(uid)
        save_json("authorized.json", data)
    await update.message.reply_text("✅ Premium verildi")

# ================== LOGIN ==================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        return
    LOGIN_STEP[uid] = "phone"
    await update.message.reply_text("📱 Telefon numarası (+90...)")

async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in LOGIN_STEP:
        return

    text = update.message.text.strip()

    if LOGIN_STEP[uid] == "phone":
        if not text.startswith("+"):
            await update.message.reply_text("❌ +90 ile başla")
            return
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(text)
        TEMP_CLIENT[uid] = {"client": client, "phone": text}
        LOGIN_STEP[uid] = "code"
        await update.message.reply_text("📩 Kodu gir (1 2 3 4 5)")

    elif LOGIN_STEP[uid] == "code":
        data = TEMP_CLIENT[uid]
        try:
            await data["client"].sign_in(data["phone"], text.replace(" ", ""))
        except SessionPasswordNeededError:
            LOGIN_STEP[uid] = "password"
            await update.message.reply_text("🔐 2FA şifre")
            return

        await start_userbot(uid, data["client"], update)
        cleanup(uid)

    elif LOGIN_STEP[uid] == "password":
        data = TEMP_CLIENT[uid]
        await data["client"].sign_in(password=text)
        await start_userbot(uid, data["client"], update)
        cleanup(uid)

def cleanup(uid):
    LOGIN_STEP.pop(uid, None)
    TEMP_CLIENT.pop(uid, None)

# ================== USERBOT ==================
async def start_userbot(uid, client, update):
    USERBOTS[uid] = client
    STOP_FLAGS[uid] = False

    @client.on(events.NewMessage(outgoing=True))
    async def handler(event):
        if STOP_FLAGS.get(uid):
            return

        text = event.raw_text

        if text == ".stop":
            STOP_FLAGS[uid] = True
            await event.reply("⛔ Durduruldu")
            return

        if text.startswith(".ig"):
            await event.reply("🌙 İyi geceler")
        if text.startswith(".gn"):
            await event.reply("☀️ Günaydın")
        if text.startswith(".t"):
            msg = text[2:].strip()
            if msg:
                await event.reply(msg)

    await client.start()
    await update.message.reply_text("✅ Userbot aktif")
    asyncio.create_task(client.run_until_disconnected())

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("pre", pre))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler))
    print("Bot çalışıyor")
    app.run_polling()

if __name__ == "__main__":
    main()
