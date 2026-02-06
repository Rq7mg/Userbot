import os
import asyncio
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================== ENV ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# ================== GLOBAL ==================
LOGIN_STEP = {}       # uid -> login step
TEMP_CLIENT = {}      # uid -> client+phone
USERBOTS = {}         # uid -> TelegramClient
STOP_FLAGS = {}       # uid -> stop

# ================== JSON UTILS ==================
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
    data = load_json("authorized.json", {"users":[]})
    return uid == OWNER_ID or uid in data["users"]

# ================== BOT COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        await update.message.reply_text("❌ Premium değilsiniz.")
        return
    await update.message.reply_text(
        "✅ Userbot hazır!\n"
        "/login → Hesap bağla\n"
        ".ig /gn /t /stop komutlarını kullanabilirsiniz."
    )

async def pre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /pre USER_ID")
        return
    try:
        uid = int(context.args[0])
    except:
        await update.message.reply_text("Geçersiz ID")
        return
    data = load_json("authorized.json", {"users":[]})
    if uid not in data["users"]:
        data["users"].append(uid)
        save_json("authorized.json", data)
    await update.message.reply_text(f"✅ {uid} premium yapıldı.")

# ================== LOGIN ==================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_premium(uid):
        await update.message.reply_text("❌ Premium değilsiniz.")
        return
    LOGIN_STEP[uid] = "phone"
    await update.message.reply_text("📱 Telefon numaranızı girin (+90...)")

async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in LOGIN_STEP:
        return
    step = LOGIN_STEP[uid]
    text = update.message.text.strip()
    
    if step == "phone":
        if not text.startswith("+"):
            await update.message.reply_text("❌ Numara + ile başlamalı")
            return
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(text)
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")
            return
        TEMP_CLIENT[uid] = {"client": client, "phone": text}
        LOGIN_STEP[uid] = "code"
        await update.message.reply_text("📩 Kodunuzu girin (sadece rakamları yazın)")

    elif step == "code":
        data = TEMP_CLIENT[uid]
        try:
            await data["client"].sign_in(data["phone"], text)
            await start_userbot(uid, data["client"], update)
            cleanup(uid)
        except SessionPasswordNeededError:
            LOGIN_STEP[uid] = "password"
            await update.message.reply_text("🔐 2FA şifrenizi girin")

    elif step == "password":
        data = TEMP_CLIENT[uid]
        try:
            await data["client"].sign_in(password=text)
            await start_userbot(uid, data["client"], update)
            cleanup(uid)
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")

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
        if text.startswith(".stop"):
            STOP_FLAGS[uid] = True
            await event.reply("⛔ İşlem durduruldu")
        elif text.startswith(".ig"):
            await event.reply("🌙 İyi geceler")
        elif text.startswith(".gn"):
            await event.reply("☀️ Günaydın")
        elif text.startswith(".t"):
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
    print("Bot başlatıldı")
    app.run_polling()

if __name__ == "__main__":
    main()
