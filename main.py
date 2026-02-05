import json
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telegram.ext import Updater, CommandHandler
from telegram import Update
from config import *

# USERBOT
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# GLOBAL STOP FLAG
STOP_FLAG = False

# AUTH
def load_auth():
    with open("authorized.json", "r") as f:
        return json.load(f)["users"]

def save_auth(users):
    with open("authorized.json", "w") as f:
        json.dump({"users": users}, f)

def is_auth(user_id):
    return user_id == OWNER_ID or user_id in load_auth()

# /pre ID
def pre(update: Update, context):
    if update.effective_user.id != OWNER_ID:
        return

    try:
        uid = int(context.args[0])
        users = load_auth()
        if uid not in users:
            users.append(uid)
            save_auth(users)
            update.message.reply_text("✅ Yetki verildi")
        else:
            update.message.reply_text("ℹ️ Zaten yetkili")
    except:
        update.message.reply_text("❌ /pre id")

# TAG SYSTEM
async def tag_all(message):
    global STOP_FLAG
    STOP_FLAG = False

    dialogs = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=100,
        hash=0
    ))

    for chat in dialogs.chats:
        if STOP_FLAG:
            break

        if chat.megagroup:
            members = await client.get_participants(chat)
            chunk = []

            for user in members:
                if STOP_FLAG:
                    break

                if user.username:
                    chunk.append(f"@{user.username}")

                if len(chunk) == 5:
                    await client.send_message(
                        chat.id,
                        message + "\n" + " ".join(chunk)
                    )
                    chunk = []
                    await asyncio.sleep(7)

# /gn
def gn(update: Update, context):
    if not is_auth(update.effective_user.id):
        return
    update.message.reply_text("▶️ Günaydın etiketleme başladı")
    asyncio.run(tag_all("🌅 Günaydın"))

# /ig
def ig(update: Update, context):
    if not is_auth(update.effective_user.id):
        return
    update.message.reply_text("▶️ İyi geceler etiketleme başladı")
    asyncio.run(tag_all("🌙 İyi geceler"))

# /t mesaj
def t(update: Update, context):
    if not is_auth(update.effective_user.id):
        return

    text = " ".join(context.args)
    if not text:
        update.message.reply_text("❌ /t mesaj")
        return

    update.message.reply_text("▶️ Etiketleme başladı")
    asyncio.run(tag_all(text))

# /stop
def stop(update: Update, context):
    global STOP_FLAG
    if not is_auth(update.effective_user.id):
        return

    STOP_FLAG = True
    update.message.reply_text("⛔ Etiketleme durduruldu")

def main():
    client.start()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("pre", pre))
    dp.add_handler(CommandHandler("gn", gn))
    dp.add_handler(CommandHandler("ig", ig))
    dp.add_handler(CommandHandler("t", t))
    dp.add_handler(CommandHandler("stop", stop))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
