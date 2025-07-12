# bot.py
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from utils.bscscan import verify_transaction
from datetime import datetime, timedelta

# Load env variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))
BEP20_WALLET = os.getenv("BEP20_WALLET")
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
GROUP_LINKS = {
    "starter": os.getenv("GROUP_STARTER"),
    "pro": os.getenv("GROUP_PRO"),
    "ultimate": os.getenv("GROUP_ULTIMATE"),
}
PLAN_PRICES = {
    "starter": 9.99,
    "pro": 19.99,
    "ultimate": 29.99
}

logging.basicConfig(level=logging.INFO)
user_data = {}
paid_users = {}  # {user_id: expiry_date}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")
    ]]
    await update.message.reply_text("🌐 Select your language / Selecciona tu idioma:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_data[query.from_user.id] = {"lang": lang}

    text = "✅ Choose your plan:" if lang == "en" else "✅ Elige tu plan:"
    buttons = [
        [InlineKeyboardButton("🔹 Starter", callback_data="plan_starter")],
        [InlineKeyboardButton("🔸 Pro", callback_data="plan_pro")],
        [InlineKeyboardButton("🔴 Ultimate", callback_data="plan_ultimate")],
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def handle_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.split('_')[1]
    uid = query.from_user.id
    user_data[uid]["plan"] = plan
    lang = user_data[uid].get("lang", "en")
    text = (
        f"✅ Send your BEP20 hash to:
`{BEP20_WALLET}`\n💸 Plan: {plan.capitalize()}"
        if lang == "en"
        else f"✅ Envía el hash de pago a:
`{BEP20_WALLET}`\n💸 Plan: {plan.capitalize()}"
    )
    await query.edit_message_text(text=text, parse_mode="Markdown")

async def handle_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    username = update.message.from_user.username or "User"
    hash_code = update.message.text.strip()

    if uid not in user_data:
        await update.message.reply_text("❗ Please start with /start.")
        return

    plan = user_data[uid].get("plan", "starter")
    lang = user_data[uid].get("lang", "en")

    await update.message.reply_text("🔍 Checking transaction...")
    valid, amount = verify_transaction(hash_code, BEP20_WALLET, USDT_CONTRACT, BSCSCAN_API_KEY)
    required = PLAN_PRICES[plan]
    lower_bound = required * 0.95

    if valid and amount >= lower_bound:
        expiry = datetime.utcnow() + timedelta(days=7)
        paid_users[uid] = expiry
        await update.message.reply_text(
            f"✅ Payment verified! Access your group: {GROUP_LINKS[plan]}"
        )
        await context.bot.send_message(chat_id=OWNER_ID,
            text=f"💸 @{username} paid for {plan.upper()} ({amount:.2f} USDT)")
    else:
        await update.message.reply_text("❌ Payment not valid or too low.")

# Scheduled check for expired users (dummy placeholder)
async def expire_check(app: Application):
    now = datetime.utcnow()
    for uid, expiry in list(paid_users.items()):
        if expiry < now:
            del paid_users[uid]
            await app.bot.send_message(chat_id=uid, text="⛔ Your subscription expired.")

# Main runner
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_lang, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(handle_plan, pattern="^plan_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))

    app.job_queue.run_repeating(lambda _: expire_check(app), interval=3600, first=10)

    logging.info("🚀 BoostIQ Bot ready")
    app.run_polling()

if __name__ == '__main__':
    main()
