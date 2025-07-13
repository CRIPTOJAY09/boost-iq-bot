import os
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from telegram import Bot
import uvicorn

# Cargar variables de entorno
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
ALERT_SECRET = os.getenv("ALERT_SECRET")

if not BOT_TOKEN or not OWNER_ID or not ALERT_SECRET:
    raise Exception("Faltan variables críticas en .env")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

@app.post("/alert")
async def send_alert(request: Request):
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {ALERT_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = await request.json()
    message = data.get("message")

    if not message:
        raise HTTPException(status_code=400, detail="Missing message")

    try:
        await bot.send_message(chat_id=OWNER_ID, text=message, parse_mode="Markdown")
        return {"status": "success", "message": "Alert sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending alert: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("alert_server:app", host="0.0.0.0", port=8000)
