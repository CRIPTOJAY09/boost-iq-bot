
import os
import time
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Configuración
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")  # Telegram ID de @CriptoJay
BEP20_WALLET = "0x6212905759a270a5860fc09f3f7c84c54470a89b"
GROUP_LINKS = {
    "starter": "https://t.me/+2XQj6r78vhk2Yjg0",
    "pro": "https://t.me/+Vvjz7LRBRpE3M2M8",
    "ultimate": "https://t.me/+PstYT5ljmh0zYjl0"
}

# Setup
logging.basicConfig(level=logging.INFO)
user_data = {}

# Verificación de pagos
def verify_tx(hash_code):
    url = f"https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash={hash_code}&apikey={os.getenv('BSCSCAN_API_KEY')}"
    r = requests.get(url)
    if r.ok and r.json()["result"]["status"] == "1":
        tx_info = requests.get(
            f"https://api.bscscan.com/api?module=account&action=txlist&address={BEP20_WALLET}&sort=desc&apikey={os.getenv('BSCSCAN_API_KEY')}"
        ).json()
        for tx in tx_info["result"]:
            if tx["hash"] == hash_code and tx["to"].lower() == BEP20_WALLET.lower():
                return True
    return False

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en'),
         InlineKeyboardButton("🇪🇸 Español", callback_data='lang_es')]
    ]
    await update.message.reply_text("🌐 Select your language / Selecciona tu idioma:", reply_markup=InlineKeyboardMarkup(keyboard))

async def language_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user_data[query.from_user.id] = {"lang": lang}
    if lang == "en":
        text = "✅ Choose your plan:"
    else:
        text = "✅ Elige tu plan:"
    buttons = [
        [InlineKeyboardButton("🔹 Starter", callback_data='plan_starter')],
        [InlineKeyboardButton("🔸 Pro", callback_data='plan_pro')],
        [InlineKeyboardButton("🔴 Ultimate", callback_data='plan_ultimate')]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def plan_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    plan = query.data.split("_")[1]
    uid = query.from_user.id
    lang = user_data.get(uid, {}).get("lang", "en")
    user_data[uid]["plan"] = plan
    msg = (
        f"✅ Send the hash of your payment to this BEP20 wallet:
`{BEP20_WALLET}`"
        if lang == "en" else
        f"✅ Envía el hash de tu pago a esta wallet BEP20:
`{BEP20_WALLET}`"
    )
    await query.edit_message_text(msg, parse_mode='Markdown')

async def handle_hash(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    hash_code = update.message.text.strip()
    if len(hash_code) != 66 or not hash_code.startswith("0x"):
        await update.message.reply_text("❌ Invalid transaction hash.")
        return

    await update.message.reply_text("🔎 Verifying your payment on BscScan...")
    if verify_tx(hash_code):
        plan = user_data.get(uid, {}).get("plan", "starter")
        await update.message.reply_text(
            f"✅ Payment verified! Join your private group:
{GROUP_LINKS[plan]}"
        )
        context.bot.send_message(chat_id=OWNER_ID, text=f"💸 New payment from @{update.message.from_user.username or 'User'} for {plan} plan.")
    else:
        await update.message.reply_text("❌ Payment not found or not confirmed.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(plan_selection, pattern="^plan_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))
    print("🚀 BoostIQ Bot ready.")
    app.run_polling()

if __name__ == '__main__':
    main()
