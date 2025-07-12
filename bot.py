import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obtener el token del bot desde las variables de entorno
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Verificar que el token existe
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje cuando se usa el comando /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"¡Hola {user.mention_html()}! Soy tu bot de Telegram.\n"
        f"Usa /help para ver los comandos disponibles."
    )

# Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje de ayuda cuando se usa el comando /help"""
    help_text = """
🤖 *Comandos disponibles:*

/start - Iniciar el bot
/help - Mostrar esta ayuda
/echo - Repetir tu mensaje
/info - Información sobre el bot

📝 También puedes enviarme cualquier mensaje y te responderé.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Comando /echo
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Repite el mensaje del usuario"""
    if context.args:
        message = ' '.join(context.args)
        await update.message.reply_text(f"📢 Echo: {message}")
    else:
        await update.message.reply_text("Uso: /echo <mensaje>")

# Comando /info
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra información sobre el bot"""
    info_text = """
ℹ️ *Información del Bot*

🤖 Nombre: Mi Bot de Telegram
🔧 Versión: 1.0
📊 Estado: Activo
🐍 Python: 3.12
📚 Librería: python-telegram-bot

¡Gracias por usar el bot! 🎉
    """
    await update.message.reply_text(info_text, parse_mode='Markdown')

# Manejador de mensajes de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto regulares"""
    message_text = update.message.text.lower()
    
    # Respuestas simples basadas en palabras clave
    if "hola" in message_text or "hi" in message_text:
        await update.message.reply_text("¡Hola! 👋 ¿Cómo estás?")
    elif "adiós" in message_text or "bye" in message_text:
        await update.message.reply_text("¡Hasta luego! 👋")
    elif "gracias" in message_text or "thanks" in message_text:
        await update.message.reply_text("¡De nada! 😊")
    elif "cómo estás" in message_text or "how are you" in message_text:
        await update.message.reply_text("¡Estoy bien, gracias por preguntar! 🤖")
    else:
        await update.message.reply_text(f"Recibí tu mensaje: '{update.message.text}'\n¡Gracias por escribir! 💬")

# Manejador de errores
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los errores que ocurren durante la ejecución"""
    logger.error(f"Error en el bot: {context.error}")
    
    # Si el error ocurre durante una actualización, intentar responder al usuario
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Ocurrió un error procesando tu mensaje. Intenta de nuevo más tarde."
        )

def main():
    """Función principal del bot"""
    try:
        # Crear la aplicación
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Registrar los manejadores de comandos
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("echo", echo_command))
        application.add_handler(CommandHandler("info", info_command))
        
        # Registrar el manejador de mensajes de texto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Registrar el manejador de errores
        application.add_error_handler(error_handler)
        
        # Iniciar el bot
        logger.info("Iniciando el bot...")
        print("🤖 Bot iniciado correctamente. Presiona Ctrl+C para detener.")
        
        # Ejecutar el bot hasta que se presione Ctrl+C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")
        print("Verifica tu token y configuración.")

if __name__ == '__main__':
    main()
