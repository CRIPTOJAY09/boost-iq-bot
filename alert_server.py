from fastapi import FastAPI, HTTPException, Header
from telegram import Bot
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# Configuración de variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("OWNER_ID")
ALERT_SECRET = os.getenv("ALERT_SECRET")

# Validar variables de entorno
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")
if not TELEGRAM_CHAT_ID:
    raise ValueError("OWNER_ID no encontrado en las variables de entorno")
if not ALERT_SECRET:
    raise ValueError("ALERT_SECRET no encontrado en las variables de entorno")

# Inicializar el bot de Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.post("/send-alert")
async def send_alert(message: dict, authorization: str = Header(None)):
    """
    Endpoint para recibir y enviar alertas a Telegram.
    - Expects a JSON body with an 'alert' field.
    - Requires 'Authorization: Bearer <ALERT_SECRET>' header.
    """
    # Verificar autenticación
    if authorization != f"Bearer {ALERT_SECRET}":
        raise HTTPException(status_code=401, detail="Invalid or missing ALERT_SECRET")

    # Extraer mensaje
    alert_message = message.get("alert")
    if not alert_message:
        raise HTTPException(status_code=400, detail="No 'alert' field provided in the request body")

    # Enviar mensaje a Telegram
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=alert_message)
        return {"status": "Alert sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send alert: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
