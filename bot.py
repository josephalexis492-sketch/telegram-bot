import json
import logging
import asyncio
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8235731870:AAGsRBubIBxSZs72EfRif1xiLKq7CUJxGsY"
DATA_FILE = "data.json"
VERIFY_TIMEOUT = 60
RAID_LIMIT = 5        # users
RAID_SECONDS = 10     # seconds window
LOCK_TIME = 60        # lockdown duration

logging.basicConfig(level=logging.INFO)

# ================= LOAD / SAVE =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "warns": {},
            "pending": {},
            "joins": []
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data_store = load_data()

# ================= NEW MEMBER + RAID CHECK =================
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    data_store["joins"].append(now)
    data_store["joins"] = [
        t for t in data_store["joins"]
        if now - t <= RAID_SECONDS
    ]

    # 🚨 RAID DETECTED
    if len(data_store["joins"]) >= RAID_LIMIT:
        await lockdown(update, context)
        return

    for member in update.message.new_chat_members:

        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            member.id,
            permissions=ChatPermissions(can_send_messages=False)
        )

        data_store["pending"][str(member.id)] = update.effective_chat.id
        save_data(data_store)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ VERIFY NOW", callback_data=f"verify_{member.id}")]
        ])

        await update.message.reply_text(
            f"👋 Welcome {member.first_name}!\n"
            f"Verify within {VERIFY_TIMEOUT}s or be removed.",
            reply_markup=keyboard
        )

        asyncio.create_task(auto_kick(member.id, update.effective_chat.id, context))

# ================= AUTO KICK =================
async def auto_kick(user_id, chat_id, context):
    await asyncio.sleep(VERIFY_TIMEOUT)

    if str(user_id) in data_store["pending"]:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            del data_store["pending"][str(user_id)]
            save_data(data_store)
            await context.bot.send_message(chat_id, "⏳ User removed (not verified).")
        except:
            pass

# ================= VERIFY BUTTON =================
async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if str(user_id) in data_store["pending"]:
        await context.bot.restrict_chat_member(
            query.message.chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        del data_store["pending"][str(user_id)]
        save_data(data_store)

        await query.edit_message_text("✅ Verification successful!")

# ================= SPAM LINK FILTER =================
async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if any(x in text for x in ["http", "t.me", "@"]):

        await update.message.delete()

        user = update.message.from_user
        user_id = str(user.id)

        warns = data_store["warns"]
        warns[user_id] = warns.get(user_id, 0) + 1
        save_data(data_store)

        if warns[user_id] >= 3:
            await context.bot.ban_chat_member(
                update.effective_chat.id,
                user.id
            )
            await context.bot.send_message(
                update.effective_chat.id,
                f"🚫 {user.first_name} banned (spam links)."
            )
        else:
            await context.bot.send_message(
                update.effective_chat.id,
                f"⚠️ {user.first_name} warned for spam ({warns[user_id]}/3)"
            )

# ================= RAID LOCKDOWN =================
async def lockdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=False)
    )

    await context.bot.send_message(
        chat_id,
        "🚨 RAID DETECTED!\n🔒 Group locked for protection."
    )

    await asyncio.sleep(LOCK_TIME)

    await context.bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=True)
    )

    await context.bot.send_message(
        chat_id,
        "✅ Group unlocked."
    )

    data_store["joins"] = []
    save_data(data_store)

# ================= WARN COMMAND =================
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    user_id = str(user.id)

    warns = data_store["warns"]
    warns[user_id] = warns.get(user_id, 0) + 1
    save_data(data_store)

    if warns[user_id] >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text("🚫 User banned (3 warns)")
    else:
        await update.message.reply_text(f"⚠️ Warned ({warns[user_id]}/3)")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(CallbackQueryHandler(verify_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))
    app.add_handler(CommandHandler("warn", warn))

    print("🔥 Ultimate Protection Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()