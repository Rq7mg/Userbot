import json, asyncio
from pyrogram import Client, filters

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSIONS_FILE = "data/sessions.json"

STOP = {}

def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE) as f:
        return json.load(f)

clients = []

for uid, session in load_sessions().items():
    app = Client(
        name=f"user_{uid}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session,
        in_memory=True
    )

    STOP[uid] = False

    @app.on_message(filters.me & filters.command("stop", "."))
    async def stop(_, m, uid=uid):
        STOP[uid] = True
        await m.reply("⛔ Durduruldu")

    async def tag_all(app, m, uid, text):
        STOP[uid] = False
        async for u in app.get_chat_members(m.chat.id):
            if STOP[uid]:
                return
            if u.user.is_bot:
                continue
            try:
                await app.send_message(m.chat.id, f"{text} {u.user.mention}")
                await asyncio.sleep(2)
            except:
                pass

    @app.on_message(filters.me & filters.command("gn", "."))
    async def gn(_, m, uid=uid, app=app):
        await tag_all(app, m, uid, "☀️ Günaydın")

    @app.on_message(filters.me & filters.command("ig", "."))
    async def ig(_, m, uid=uid, app=app):
        await tag_all(app, m, uid, "🌙 İyi geceler")

    @app.on_message(filters.me & filters.command("t", "."))
    async def t(_, m, uid=uid, app=app):
        if len(m.command) < 2:
            return
        await tag_all(app, m, uid, m.text.split(" ", 1)[1])

    clients.append(app)

print(f"🚀 {len(clients)} userbot başlatılıyor")

async def main():
    await asyncio.gather(*(c.start() for c in clients))
    await asyncio.Event().wait()

asyncio.run(main())
