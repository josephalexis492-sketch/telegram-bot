import json
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8235731870:AAGsRBubIBxSZs72EfRif1xiLKq7CUJxGsY"
OWNER_ID = 6548935235
DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)

# ================= LOAD / SAVE =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "key": None,
            "apk": None,
            "warns": {}
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data_store = load_data()

# ================= OWNER SAVE KEY/APK =================
async def save_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if update.message.text:
        data_store["key"] = update.message.text
        save_data(data_store)
        await update.message.reply_text("✅ Key saved!")

    elif update.message.document:
        data_store["apk"] = update.message.document.file_id
        save_data(data_store)
        await update.message.reply_text("✅ APK saved!")

# ================= KEY COMMAND =================
async def send_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if data_store["key"]:
        await update.message.reply_text(f"🔐 VIP KEY:\n\n{data_store['key']}")
    else:
        await update.message.reply_text("❌ No key set.")

# ================= APK COMMAND =================
async def send_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if data_store["apk"]:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=data_store["apk"]
        )
    else:
        await update.message.reply_text("❌ No APK uploaded.")

# ================= WARN SYSTEM =================
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    user_id = str(user.id)

    warns = data_store["warns"]
    warns[user_id] = warns.get(user_id, 0) + 1

    save_data(data_store)

    if warns[user_id] >= 3:
        await context.bot.ban_chat_member(
            update.effective_chat.id,
            user.id
        )
        await update.message.reply_text(
            f"🚫 {user.first_name} banned (3 warns)"
        )
    else:
        await update.message.reply_text(
            f"⚠️ {user.first_name} warned ({warns[user_id]}/3)"
        )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.TEXT | filters.Document.ALL),
            save_private
        )
    )

    app.add_handler(CommandHandler("key", send_key))
    app.add_handler(CommandHandler("injc", send_apk))
    app.add_handler(CommandHandler("warn", warn))

    print("🔥 Rose-style bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()