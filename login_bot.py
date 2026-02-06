import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

bot = TelegramClient("loginbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

SESSIONS = {}
STEPS = {}

@bot.on(events.NewMessage(from_users=OWNER_ID))
async def handler(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if text == "/login":
        STEPS[uid] = "phone"
        await event.reply("📱 Telefon numaranı gir gardaşım (+90...)")
        return

    if uid not in STEPS:
        return

    if STEPS[uid] == "phone":
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(text)

        SESSIONS[uid] = {
            "client": client,
            "phone": text
        }
        STEPS[uid] = "code"
        await event.reply("📩 Telegram kodunu gir (1 2 3 4 5)")
        return

    if STEPS[uid] == "code":
        data = SESSIONS[uid]
        try:
            await data["client"].sign_in(data["phone"], text.replace(" ", ""))
        except SessionPasswordNeededError:
            STEPS[uid] = "password"
            await event.reply("🔐 2FA şifreni gir")
            return

        session = data["client"].session.save()
        await event.reply(
            "✅ String Session üretildi:\n\n"
            f"`{session}`\n\n"
            "⚠️ Bunu ENV içine SESSION_STRING olarak ekle",
            parse_mode="md"
        )
        await data["client"].disconnect()
        STEPS.pop(uid)
        return

    if STEPS[uid] == "password":
        data = SESSIONS[uid]
        await data["client"].sign_in(password=text)

        session = data["client"].session.save()
        await event.reply(
            "✅ String Session üretildi:\n\n"
            f"`{session}`",
            parse_mode="md"
        )
        await data["client"].disconnect()
        STEPS.pop(uid)

print("🔐 Login bot çalışıyor...")
bot.run_until_disconnected()
