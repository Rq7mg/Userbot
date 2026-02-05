import os, json, asyncio
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
OWNER_ID = int(os.environ["OWNER_ID"])

LOGIN_STATE = {}     # user_id: step
TEMP_CLIENT = {}     # user_id: telethon client + phone
STOP_FLAGS = {}      # user_id: stop durumu

# ---------- JSON UTILS ----------
def load_json(name, default):
    if not os.path.exists(name):
        with open(name, "w") as f:
            json.dump(default, f)
    with open(name) as f:
        return json.load(f)

def save_json(name, data):
    with open(name, "w") as f:
        json.dump(data, f)

# ---------- AUTH ----------
def is_premium(uid):
    data = load_json("authorized.json", {"users": []})
    return uid == OWNER_ID or uid in data["users"]

# ---------- START ----------
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_premium(uid):
        update.message.reply_text(
            "⚠️ Premium değilsiniz.\n"
            "Premium için @OfficialKiyici hesabına yazın."
        )
    else:
        update.message.reply_text(
            "✅ Premium aktif.\n"
            "/login → Hesap bağla\n"
            "/logout → Hesap sil\n"
            "/gn /ig /t /stop"
        )

# ---------- PRE KOMUTU ----------
def pre(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id

    if sender_id != OWNER_ID:
        update.message.reply_text("⛔ Bu komutu kullanamazsın.")
        return

    if not context.args:
        update.message.reply_text("❌ Kullanım: /pre USER_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("❌ Geçersiz ID")
        return

    data = load_json("authorized.json", {"users": []})

    if target_id in data["users"]:
        update.message.reply_text("ℹ️ Bu kullanıcı zaten premium.")
        return

    data["users"].append(target_id)
    save_json("authorized.json", data)

    update.message.reply_text(f"✅ {target_id} premium yapıldı.")

# ---------- LOGIN FLOW ----------
def login(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_premium(uid):
        update.message.reply_text("⛔ Premium değilsiniz.")
        return
    LOGIN_STATE[uid] = "phone"
    update.message.reply_text("📱 Telefon numaranızı girin (+90...)")

def handle_login(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid not in LOGIN_STATE:
        return

    text = update.message.text.strip()
    step = LOGIN_STATE[uid]

    if step == "phone":
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        asyncio.create_task(start_phone_step(update, uid, client, text))

    elif step == "code":
        data = TEMP_CLIENT[uid]
        asyncio.create_task(start_code_step(update, uid, data, text))

    elif step == "password":
        data = TEMP_CLIENT[uid]
        asyncio.create_task(start_password_step(update, uid, data, text))

# ---------- ASYNC LOGIN STEPS ----------
async def start_phone_step(update, uid, client, phone):
    await client.connect()
    await client.send_code_request(phone)
    TEMP_CLIENT[uid] = {"client": client, "phone": phone}
    LOGIN_STATE[uid] = "code"
    update.message.reply_text("📩 Telegram kodunu girin")

async def start_code_step(update, uid, data, code):
    try:
        await data["client"].sign_in(data["phone"], code)
        save_session(uid, data["client"])
        cleanup(uid)
        update.message.reply_text("✅ Hesap bağlandı")
    except SessionPasswordNeededError:
        LOGIN_STATE[uid] = "password"
        update.message.reply_text("🔐 2FA şifresini girin")

async def start_password_step(update, uid, data, password):
    await data["client"].sign_in(password=password)
    save_session(uid, data["client"])
    cleanup(uid)
    update.message.reply_text("✅ Hesap bağlandı")

def save_session(uid, client):
    sessions = load_json("sessions.json", {})
    sessions[str(uid)] = client.session.save()
    save_json("sessions.json", sessions)

def cleanup(uid):
    LOGIN_STATE.pop(uid, None)
    TEMP_CLIENT.pop(uid, None)

# ---------- USERBOT ----------
def get_client(uid):
    sessions = load_json("sessions.json", {})
    if str(uid) not in sessions:
        return None
    return TelegramClient(StringSession(sessions[str(uid)]), API_ID, API_HASH)

async def tag_all(uid, text):
    STOP_FLAGS[uid] = False
    client = get_client(uid)
    if not client:
        return

    await client.start()
    dialogs = await client.get_dialogs()
    for d in dialogs:
        if STOP_FLAGS.get(uid):
            break
        if d.is_group:
            users = await client.get_participants(d)
            chunk = []
            for u in users:
                if STOP_FLAGS.get(uid):
                    break
                if u.username:
                    chunk.append(f"@{u.username}")
                if len(chunk) == 5:
                    await client.send_message(d.id, text + "\n" + " ".join(chunk))
                    chunk = []
                    await asyncio.sleep(7)

# ---------- COMMANDS ----------
def gn(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    asyncio.create_task(tag_all(uid, "🌅 Günaydın"))

def ig(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    asyncio.create_task(tag_all(uid, "🌙 İyi geceler"))

def t(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    msg = " ".join(context.args)
    if msg:
        asyncio.create_task(tag_all(uid, msg))
    else:
        update.message.reply_text("❌ /t mesaj")

def stop(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    STOP_FLAGS[uid] = True
    update.message.reply_text("⛔ İşlem durduruldu")

def logout(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    sessions = load_json("sessions.json", {})
    sessions.pop(str(uid), None)
    save_json("sessions.json", sessions)
    update.message.reply_text("🚪 Hesap silindi")

# ---------- MAIN ----------
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("login", login))
    dp.add_handler(CommandHandler("logout", logout))
    dp.add_handler(CommandHandler("gn", gn))
    dp.add_handler(CommandHandler("ig", ig))
    dp.add_handler(CommandHandler("t", t))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("pre", pre))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_login))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
