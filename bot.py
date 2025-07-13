import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from utils.bscscan import verify_transaction
from datetime import datetime, timedelta
import json

# Load env variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
BEP20_WALLET = os.getenv("BEP20_WALLET")
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"

# Verificar variables de entorno críticas
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

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Almacenamiento de datos (en producción usar una base de datos)
user_data = {}
paid_users = {}  # {user_id: expiry_date}

# Mensajes multiidioma
MESSAGES = {
    "en": {
        "select_language": "🌐 Select your language:",
        "choose_plan": "✅ Choose your plan:",
        "payment_info": "💰 Plan: {plan}\n💵 Price: ${price} USDT\n\n📤 Send exactly ${price} USDT to this BEP20 address:\n\n`{wallet}`\n\n⚠️ After payment, send your transaction hash here.",
        "send_hash": "📝 Now send your transaction hash:",
        "start_first": "❗ Please start with /start first.",
        "checking_payment": "🔍 Verifying your payment...\n⏰ This may take a few seconds.",
        "payment_verified": "✅ Payment verified successfully!\n🎉 Welcome to {plan} plan!\n\n🔗 Access your group: {link}",
        "payment_failed": "❌ Payment verification failed.\n\nPossible reasons:\n• Transaction not found\n• Amount too low (minimum: ${min_amount})\n• Wrong recipient address\n• Transaction too old\n\nPlease try again or contact support.",
        "subscription_expired": "⛔ Your subscription has expired.\n\nUse /start to renew your access.",
        "invalid_hash": "❌ Invalid transaction hash format.\n\nPlease send a valid BSC transaction hash (66 characters starting with 0x).",
        "help_text": "🤖 *BoostIQ Bot Help*\n\n/start - Start the bot and select plan\n/help - Show this help message\n/status - Check your subscription status\n\n💡 How to use:\n1. Select your language\n2. Choose a plan\n3. Send USDT to the provided address\n4. Send your transaction hash\n5. Get instant access to your group!",
        "status_active": "✅ *Subscription Status: ACTIVE*\n\n📋 Plan: {plan}\n⏰ Expires: {expiry}\n🔗 Group: {link}",
        "status_inactive": "❌ *Subscription Status: INACTIVE*\n\nUse /start to purchase access."
    },
    "es": {
        "select_language": "🌐 Selecciona tu idioma:",
        "choose_plan": "✅ Elige tu plan:",
        "payment_info": "💰 Plan: {plan}\n💵 Precio: ${price} USDT\n\n📤 Envía exactamente ${price} USDT a esta dirección BEP20:\n\n`{wallet}`\n\n⚠️ Después del pago, envía tu hash de transacción aquí.",
        "send_hash": "📝 Ahora envía tu hash de transacción:",
        "start_first": "❗ Por favor inicia con /start primero.",
        "checking_payment": "🔍 Verificando tu pago...\n⏰ Esto puede tomar unos segundos.",
        "payment_verified": "✅ ¡Pago verificado exitosamente!\n🎉 ¡Bienvenido al plan {plan}!\n\n🔗 Accede a tu grupo: {link}",
        "payment_failed": "❌ Verificación de pago fallida.\n\nPosibles razones:\n• Transacción no encontrada\n• Cantidad muy baja (mínimo: ${min_amount})\n• Dirección de destinatario incorrecta\n• Transacción muy antigua\n\nIntenta de nuevo o contacta soporte.",
        "subscription_expired": "⛔ Tu suscripción ha expirado.\n\nUsa /start para renovar tu acceso.",
        "invalid_hash": "❌ Formato de hash de transacción inválido.\n\nEnvía un hash de transacción BSC válido (66 caracteres comenzando con 0x).",
        "help_text": "🤖 *Ayuda del Bot BoostIQ*\n\n/start - Iniciar el bot y seleccionar plan\n/help - Mostrar este mensaje de ayuda\n/status - Verificar estado de suscripción\n\n💡 Cómo usar:\n1. Selecciona tu idioma\n2. Elige un plan\n3. Envía USDT a la dirección proporcionada\n4. Envía tu hash de transacción\n5. ¡Obtén acceso instantáneo a tu grupo!",
        "status_active": "✅ *Estado de Suscripción: ACTIVA*\n\n📋 Plan: {plan}\n⏰ Expira: {expiry}\n🔗 Grupo: {link}",
        "status_inactive": "❌ *Estado de Suscripción: INACTIVA*\n\nUsa /start para comprar acceso."
    }
}

def get_message(user_id: int, key: str, **kwargs) -> str:
    """Obtener mensaje en el idioma del usuario"""
    lang = user_data.get(user_id, {}).get("lang", "en")
    message = MESSAGES[lang].get(key, MESSAGES["en"][key])
    return message.format(**kwargs) if kwargs else message

def is_valid_hash(hash_str: str) -> bool:
    """Validar formato de hash de transacción"""
    return (
        isinstance(hash_str, str) and
        len(hash_str) == 66 and
        hash_str.startswith("0x") and
        all(c in "0123456789abcdefABCDEF" for c in hash_str[2:])
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.message.from_user.id
    
    # Resetear datos del usuario
    user_data[user_id] = {}
    
    keyboard = [[
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")
    ]]
    
    await update.message.reply_text(
        get_message(user_id, "select_language"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    user_id = update.message.from_user.id
    await update.message.reply_text(
        get_message(user_id, "help_text"),
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    user_id = update.message.from_user.id
    
    if user_id in paid_users:
        expiry = paid_users[user_id]
        if expiry > datetime.utcnow():
            plan = user_data.get(user_id, {}).get("plan", "unknown")
            group_link = GROUP_LINKS.get(plan, "N/A")
            
            await update.message.reply_text(
                get_message(user_id, "status_active", 
                          plan=plan.capitalize(),
                          expiry=expiry.strftime("%Y-%m-%d %H:%M UTC"),
                          link=group_link),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                get_message(user_id, "status_inactive"),
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            get_message(user_id, "status_inactive"),
            parse_mode="Markdown"
        )

async def handle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de idioma"""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.split('_')[1]
    user_id = query.from_user.id
    
    user_data[user_id] = {"lang": lang}
    
    buttons = [
        [InlineKeyboardButton("🔹 Starter ($9.99)", callback_data="plan_starter")],
        [InlineKeyboardButton("🔸 Pro ($19.99)", callback_data="plan_pro")],
        [InlineKeyboardButton("🔴 Ultimate ($29.99)", callback_data="plan_ultimate")],
    ]
    
    await query.edit_message_text(
        text=get_message(user_id, "choose_plan"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de plan"""
    query = update.callback_query
    await query.answer()
    
    plan = query.data.split('_')[1]
    user_id = query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]["plan"] = plan
    user_data[user_id]["waiting_for_hash"] = True
    
    price = PLAN_PRICES[plan]
    
    await query.edit_message_text(
        text=get_message(user_id, "payment_info", 
                        plan=plan.capitalize(),
                        price=price,
                        wallet=BEP20_WALLET),
        parse_mode="Markdown"
    )

async def handle_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar hash de transacción"""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "User"
    hash_code = update.message.text.strip()
    
    # Verificar si el usuario está en el flujo correcto
    if user_id not in user_data or not user_data[user_id].get("waiting_for_hash"):
        await update.message.reply_text(get_message(user_id, "start_first"))
        return
    
    # Validar formato del hash
    if not is_valid_hash(hash_code):
        await update.message.reply_text(get_message(user_id, "invalid_hash"))
        return
    
    plan = user_data[user_id].get("plan", "starter")
    
    # Mensaje de verificación
    checking_msg = await update.message.reply_text(
        get_message(user_id, "checking_payment")
    )
    
    try:
        # Verificar transacción
        valid, amount = verify_transaction(hash_code, BEP20_WALLET, USDT_CONTRACT, BSCSCAN_API_KEY)
        required = PLAN_PRICES[plan]
        lower_bound = required * 0.95  # 5% de tolerancia
        
        if valid and amount >= lower_bound:
            # Pago verificado exitosamente
            expiry = datetime.utcnow() + timedelta(days=30)  # 30 días en lugar de 7
            paid_users[user_id] = expiry
            user_data[user_id]["waiting_for_hash"] = False
            
            group_link = GROUP_LINKS.get(plan, "Contact support for group access")
            
            await checking_msg.edit_text(
                get_message(user_id, "payment_verified", 
                          plan=plan.capitalize(),
                          link=group_link)
            )
            
            # Notificar al owner
            if OWNER_ID:
                try:
                    await context.bot.send_message(
                        chat_id=OWNER_ID,
                        text=f"💸 *Nueva suscripción*\n\n"
                             f"👤 Usuario: @{username} (ID: {user_id})\n"
                             f"📋 Plan: {plan.upper()}\n"
                             f"💰 Cantidad: {amount:.2f} USDT\n"
                             f"🔗 Hash: `{hash_code}`\n"
                             f"⏰ Expira: {expiry.strftime('%Y-%m-%d %H:%M UTC')}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Error enviando notificación al owner: {e}")
            
        else:
            # Pago no válido
            await checking_msg.edit_text(
                get_message(user_id, "payment_failed", min_amount=required)
            )
            
    except Exception as e:
        logger.error(f"Error verificando transacción: {e}")
        await checking_msg.edit_text(
            "❌ Error verificando la transacción. Intenta de nuevo más tarde."
        )

async def expire_check(context: ContextTypes.DEFAULT_TYPE):
    """Verificar suscripciones expiradas"""
    try:
        now = datetime.utcnow()
        expired_users = []
        
        for user_id, expiry in paid_users.items():
            if expiry < now:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del paid_users[user_id]
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_message(user_id, "subscription_expired")
                )
            except Exception as e:
                logger.error(f"Error enviando mensaje de expiración a {user_id}: {e}")
        
        if expired_users:
            logger.info(f"Suscripciones expiradas: {len(expired_users)} usuarios")
            
    except Exception as e:
        logger.error(f"Error en verificación de expiración: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Manejar errores"""
    logger.error(f"Error en el bot: {context.error}")
    
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error. Intenta de nuevo más tarde."
            )
        except Exception as e:
            logger.error(f"Error enviando mensaje de error: {e}")

def main():
    """Función principal"""
    try:
        # Crear aplicación
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Registrar handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CallbackQueryHandler(handle_lang, pattern="^lang_"))
        app.add_handler(CallbackQueryHandler(handle_plan, pattern="^plan_"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))
        
        # Registrar manejador de errores
        app.add_error_handler(error_handler)
        
        # Programar verificación de expiración cada hora
        app.job_queue.run_repeating(expire_check, interval=3600, first=10)
        
        logger.info("🚀 BoostIQ Bot iniciado correctamente")
        print("🤖 BoostIQ Bot running. Press Ctrl+C to stop.")
        
        # Iniciar polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")

if __name__ == '__main__':
    main()
