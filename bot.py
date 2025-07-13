import os
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv
import json

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
BEP20_WALLET = os.getenv("WALLET_BEP20")
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"

GROUP_LINKS = {
    "starter": os.getenv("GROUP_LINK_STARTER"),
    "pro": os.getenv("GROUP_LINK_PRO"),
    "ultimate": os.getenv("GROUP_LINK_ULTIMATE"),
}

PLAN_PRICES = {
    "starter": 9.99,
    "pro": 19.99,
    "ultimate": 29.99
}

PLAN_DURATIONS = {
    "starter": 30,
    "pro": 90,
    "ultimate": 180
}

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")
if not BSCSCAN_API_KEY:
    raise ValueError("BSCSCAN_API_KEY no encontrado en las variables de entorno")
if not OWNER_ID:
    raise ValueError("OWNER_ID no encontrado en las variables de entorno")
if not BEP20_WALLET:
    raise ValueError("WALLET_BEP20 no encontrado en las variables de entorno")
if not all(GROUP_LINKS.values()):
    raise ValueError("Faltan GROUP_LINK_STARTER, GROUP_LINK_PRO o GROUP_LINK_ULTIMATE")

SUBSCRIPTIONS_FILE = "subscriptions.json"

def load_subscriptions():
    try:
        with open(SUBSCRIPTIONS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_subscriptions(subscriptions):
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subscriptions, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Español 🇪🇸", callback_data="lang_es"),
         InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¡Bienvenido a BoostIQ! Elige tu idioma:", reply_markup=reply_markup)

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data["language"] = lang
    keyboard = [
        [InlineKeyboardButton("Starter ($9.99)", callback_data="plan_starter"),
         InlineKeyboardButton("Pro ($19.99)", callback_data="plan_pro")],
        [InlineKeyboardButton("Ultimate ($29.99)", callback_data="plan_ultimate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Selecciona un plan:" if lang == "es" else "Select a plan:",
        reply_markup=reply_markup
    )

async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.split("_")[1]
    context.user_data["plan"] = plan
    lang = context.user_data.get("language", "es")
    price = PLAN_PRICES[plan]
    await query.message.reply_text(
        f"Has elegido el plan {plan.capitalize()} (${price}).\n"
        f"Por favor, envía {price} USDT (BEP20) a esta dirección: `{BEP20_WALLET}`\n"
        f"Una vez realizado el pago, envía el hash de la transacción."
        if lang == "es" else
        f"You've chosen the {plan.capitalize()} plan (${price}).\n"
        f"Please send {price} USDT (BEP20) to this address: `{BEP20_WALLET}`\n"
        f"Once the payment is made, send the transaction hash."
    )

async def verify_payment(tx_hash: str, plan: str) -> bool:
    url = f"https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash={tx_hash}&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "1":
            tx_details = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={USDT_CONTRACT}&address={BEP20_WALLET}&apikey={BSCSCAN_API_KEY}"
            tx_response = requests.get(tx_details)
            tx_data = tx_response.json()
            for tx in tx_data.get("result", []):
                if tx["hash"] == tx_hash:
                    amount = float(tx["value"]) / 10**18
                    expected_amount = PLAN_PRICES.get(plan, 9.99)
                    if abs(amount - expected_amount) < 0.01:
                        return True
            return False
        return False
    except Exception as e:
        logger.error(f"Error verificando pago: {e}")
        return False

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_hash = update.message.text.strip()
    lang = context.user_data.get("language", "es")
    plan = context.user_data.get("plan", "starter")
    
    if await verify_payment(tx_hash, plan):
        user_id = str(update.message.from_user.id)
        subscriptions = load_subscriptions()
        subscriptions[user_id] = {
            "plan": plan,
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=PLAN_DURATIONS[plan])).isoformat()
        }
        save_subscriptions(subscriptions)
        
        group_link = GROUP_LINKS.get(plan)
        await update.message.reply_text(
            f"¡Pago verificado! Únete al grupo: {group_link}"
            if lang == "es" else
            f"Payment verified! Join the group: {group_link}"
        )
        await context.bot.send_message(
            OWNER_ID,
            f"Nueva suscripción: {update.message.from_user.username} ({plan.capitalize()})"
        )
    else:
        await update.message.reply_text(
            "Pago no válido. Verifica el hash o contacta al soporte."
            if lang == "es" else
            "Invalid payment. Please check the hash or contact support."
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    subscriptions = load_subscriptions()
    lang = context.user_data.get("language", "es")
    if user_id in subscriptions:
        plan = subscriptions[user_id]["plan"]
        end_date = datetime.fromisoformat(subscriptions[user_id]["end_date"])
        await update.message.reply_text(
            f"Tu plan: {plan.capitalize()}\nExpira: {end_date.strftime('%Y-%m-%d')}"
            if lang == "es" else
            f"Your plan: {plan.capitalize()}\nExpires: {end_date.strftime('%Y-%m-%d')}"
        )
    else:
        await update.message.reply_text(
            "No tienes una suscripción activa." if lang == "es" else "You don't have an active subscription."
        )

async def check_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    subscriptions = load_subscriptions()
    now = datetime.now()
    for user_id, data in list(subscriptions.items()):
        end_date = datetime.fromisoformat(data["end_date"])
        if now > end_date:
            del subscriptions[user_id]
            await context.bot.send_message(
                OWNER_ID,
                f"Usuario {user_id} con suscripción expirada ({data['plan']})."
            )
    save_subscriptions(subscriptions)

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CallbackQueryHandler(select_language, pattern="lang_.*"))
        app.add_handler(CallbackQueryHandler(select_plan, pattern="plan_.*"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_payment))
        app.job_queue.run_repeating(check_subscriptions, interval=86400, first=10)
        logger.info("🚀 BoostIQ Bot iniciado con polling")
        app.run_polling()
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    main()
