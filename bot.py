
import os
import logging
import asyncio
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from datetime import datetime, timedelta
import json
from aiohttp import web

# Load env variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
BEP20_WALLET = os.getenv("BEP20_WALLET")
ALERT_SECRET = os.getenv("ALERT_SECRET")
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")
if not BSCSCAN_API_KEY:
    raise ValueError("BSCSCAN_API_KEY no encontrado en las variables de entorno")
if not OWNER_ID:
    raise ValueError("OWNER_ID no encontrado en las variables de entorno")
if not BEP20_WALLET:
    raise ValueError("BEP20_WALLET no encontrado en las variables de entorno")

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data = {}
paid_users = {}

# API de alertas

async def alert_handler(request):
    try:
        data = await request.json()
        secret = data.get("secret")
        message = data.get("message")

        if secret != ALERT_SECRET:
            return web.json_response({"error": "Unauthorized"}, status=401)

        if not message:
            return web.json_response({"error": "No message provided"}, status=400)

        app = request.app["telegram_bot"]
        await app.bot.send_message(chat_id=OWNER_ID, text=message)
        return web.json_response({"status": "Message sent"})
    except Exception as e:
        logger.error(f"Error in alert_handler: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Main app

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()

        # Asegúrate de que los handlers estén registrados en tu versión extendida

        app.job_queue.run_repeating(lambda context: None, interval=3600, first=10)

        web_app = web.Application()
        web_app["telegram_bot"] = app
        web_app.router.add_post("/api/send-alert", alert_handler)

        logger.info("🚀 BoostIQ Bot iniciado con API de alertas")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
            webhook_app=web_app,
        )
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")

if __name__ == '__main__':
    main()
