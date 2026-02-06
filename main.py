from pyrogram import Client, filters
import os

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

STOP = False

@app.on_message(filters.me & filters.command("alive", "."))
async def alive(_, m):
    await m.reply(" userbot aktif")

async def tag_all(m, text):
    global STOP
    STOP = False
    count = 0

    async for member in app.get_chat_members(m.chat.id):
        if STOP:
            await m.reply("⛔ Durduruldu gardaş")
            return
        if member.user.is_bot:
            continue
        try:
            await app.send_message(m.chat.id, f"{text} {member.user.mention}")
            count += 1
            await asyncio.sleep(2)
        except:
            pass

    await m.reply(f"✅ Bitti ({count} kişi)")

@app.on_message(filters.me & filters.command("gn", "."))
async def gn(_, m):
    await tag_all(m, "☀️ Günaydın")

@app.on_message(filters.me & filters.command("ig", "."))
async def ig(_, m):
    await tag_all(m, "🌙 İyi geceler")

@app.on_message(filters.me & filters.command("t", "."))
async def t(_, m):
    if len(m.command) < 2:
        await m.reply("❌ .t mesaj")
        return
    await tag_all(m, m.text.split(" ", 1)[1])

@app.on_message(filters.me & filters.command("stop", "."))
async def stop(_, m):
    global STOP
    STOP = True

print("🚀 Userbot başlatıldı kuzenn")
app.run()
