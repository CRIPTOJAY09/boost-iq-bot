import os
import logging
import telegram
from fastapi import FastAPI, Request
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALERT_SECRET = os.getenv("ALERT_SECRET")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Inicializar bot y FastAPI
bot = telegram.Bot(token=BOT_TOKEN)
app = FastAPI()

@app.post("/alert")
async def send_alert(request: Request):
    try:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {ALERT_SECRET}":
            return {"error": "No autorizado"}, 401

        data = await request.json()
        message = data.get("message", "")

        if not message:
            return {"error": "Mensaje vacío"}, 400

        await bot.send_message(chat_id=OWNER_ID, text=message, parse_mode="Markdown")
        logger.info(f"Alerta enviada a {OWNER_ID}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error enviando alerta: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    uvicorn.run("alert_server:app", host="0.0.0.0", port=8000)
