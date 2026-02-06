import os, json, asyncio, random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# ---------------- ENV ----------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
OWNER_ID = int(os.environ["OWNER_ID"])

# ---------------- GLOBAL ----------------
LOGIN_STATE = {}   # user_id: step
TEMP_CLIENT = {}   # user_id: client + phone
STOP_FLAGS = {}    # user_id: stop durumu

# ---------------- JSON UTILS ----------------
def load_json(name, default):
    if not os.path.exists(name):
        with open(name, "w") as f:
            json.dump(default, f)
    with open(name) as f:
        return json.load(f)

def save_json(name, data):
    with open(name, "w") as f:
        json.dump(data, f)

# ---------------- AUTH ----------------
def is_premium(uid):
    data = load_json("authorized.json", {"users": []})
    return uid == OWNER_ID or uid in data["users"]

def give_premium(target_id):
    data = load_json("authorized.json", {"users": []})
    if target_id not in data["users"]:
        data["users"].append(target_id)
        save_json("authorized.json", data)
        return True
    return False

# ---------------- LOGIN ----------------
async def start(update: Update, context):
    uid = update.effective_user.id
    if not is_premium(uid):
        await update.message.reply_text(
            "⚠️ Premium değilsiniz.\nPremium için owner ile iletişime geçin."
        )
        return
    await update.message.reply_text(
        "✅ Premium aktif.\n.login → Hesap bağla\n.logout → Hesap sil\n.gn/.ig/.t → Etiketleme\n.stop → Durdur"
    )

async def pre(update: Update, context):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("⛔ Bu komutu sadece owner kullanabilir.")
        return
    if not context.args:
        await update.message.reply_text("❌ Kullanım: /pre <user_id>")
        return
    try:
        target_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Geçersiz ID")
        return
    if give_premium(target_id):
        await update.message.reply_text(f"✅ {target_id} premium yapıldı.")
    else:
        await update.message.reply_text("ℹ️ Kullanıcı zaten premium.")

# ---------------- LOGIN HANDLER ----------------
async def login(update: Update, context):
    uid = update.effective_user.id
    if not is_premium(uid):
        await update.message.reply_text("⛔ Premium değilsiniz.")
        return
    LOGIN_STATE[uid] = "phone"
    await update.message.reply_text("📱 Telefon numaranızı girin (+90...)")

async def handle_login(update: Update, context):
    uid = update.effective_user.id
    if uid not in LOGIN_STATE:
        return
    text = update.message.text.strip()
    step = LOGIN_STATE[uid]
    if step == "phone":
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        asyncio.create_task(async_login_phone(update, uid, client, text))
    elif step == "code":
        data = TEMP_CLIENT[uid]
        asyncio.create_task(async_login_code(update, uid, data, text))
    elif step == "password":
        data = TEMP_CLIENT[uid]
        asyncio.create_task(async_login_password(update, uid, data, text))

async def async_login_phone(update, uid, client, phone):
    try:
        await client.connect()
        await client.send_code_request(phone)
        TEMP_CLIENT[uid] = {"client": client, "phone": phone}
        LOGIN_STATE[uid] = "code"
        await update.message.reply_text("📩 Telegram kodunu girin.")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def async_login_code(update, uid, data, code):
    try:
        await data["client"].sign_in(data["phone"], code)
        save_session(uid, data["client"])
        cleanup(uid)
        await update.message.reply_text("✅ Hesap bağlandı")
    except SessionPasswordNeededError:
        LOGIN_STATE[uid] = "password"
        await update.message.reply_text("🔐 2FA şifresini girin")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def async_login_password(update, uid, data, password):
    try:
        await data["client"].sign_in(password=password)
        save_session(uid, data["client"])
        cleanup(uid)
        await update.message.reply_text("✅ Hesap bağlandı")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

def save_session(uid, client):
    sessions = load_json("sessions.json", {})
    sessions[str(uid)] = client.session.save()
    save_json("sessions.json", sessions)

def cleanup(uid):
    LOGIN_STATE.pop(uid, None)
    TEMP_CLIENT.pop(uid, None)

def get_client(uid):
    sessions = load_json("sessions.json", {})
    if str(uid) not in sessions:
        return None
    return TelegramClient(StringSession(sessions[str(uid)]), API_ID, API_HASH)

async def logout(update, context):
    uid = update.effective_user.id
    sessions = load_json("sessions.json", {})
    sessions.pop(str(uid), None)
    save_json("sessions.json", sessions)
    await update.message.reply_text("🚪 Hesap silindi")

# ---------------- TAGGING ----------------
STOP_FLAGS = {}

async def tag_all(client, user_id, chat_id, text=None, reply_msg=None):
    STOP_FLAGS[user_id] = False
    if not client:
        return
    await client.start()
    try:
        if reply_msg:
            participants = await client.get_participants(chat_id)
            for u in participants:
                if STOP_FLAGS.get(user_id):
                    break
                mention = f"[{u.first_name}](tg://user?id={u.id})"
                msg = (text + " " + mention) if text else mention
                await client.send_message(chat_id, msg, parse_mode="md")
                await asyncio.sleep(2)
    except Exception as e:
        print(f"Tag error: {e}")

async def gn(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    reply = update.message.reply_to_message
    client = get_client(user_id)
    asyncio.create_task(tag_all(client, user_id, chat_id, text="🌞 Günaydın", reply_msg=reply))

async def ig(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    reply = update.message.reply_to_message
    client = get_client(user_id)
    asyncio.create_task(tag_all(client, user_id, chat_id, text="🌙 İyi geceler", reply_msg=reply))

async def t(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    reply = update.message.reply_to_message
    text = " ".join(context.args)
    client = get_client(user_id)
    asyncio.create_task(tag_all(client, user_id, chat_id, text=text, reply_msg=reply))

async def stop(update, context):
    user_id = update.effective_user.id
    STOP_FLAGS[user_id] = True
    await update.message.reply_text("⛔ İşlem durduruldu")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pre", pre))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("gn", gn))
    app.add_handler(CommandHandler("ig", ig))
    app.add_handler(CommandHandler("t", t))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_login))

    print("Userbot başlatıldı...")
    app.run_polling()

if __name__ == "__main__":
    main()
