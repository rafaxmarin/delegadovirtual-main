from telegram import Update
from telegram.ext import ContextTypes
from src.config import Config
from src.presentation.keyboards import get_auth_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start - Inicio del bot"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if db.es_profesor_verificado(user.id):
        await update.message.reply_text(
            f"👋 ¡Bienvenido de nuevo, {user.first_name}!\n\n"
            "Escribe /menu para ver las opciones disponibles o "
            "simplemente dime qué necesitas hacer."
        )
        return
    
    db.registrar_profesor(user.id, user.username or user.first_name)
    
    await update.message.reply_text(
        "🤖 *Delegado Virtual - UDO Monagas*\n\n"
        "Este bot es de uso exclusivo para profesores de la "
        "Universidad de Oriente, Núcleo Monagas.\n\n"
        "¿Eres profesor?",
        parse_mode='Markdown',
        reply_markup=get_auth_keyboard()
    )

async def button_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones de autenticación"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "no_profesor":
        await query.edit_message_text(
            "Lo siento, este bot es exclusivo para profesores de la UDO Monagas. "
            "Si eres estudiante, por favor contacta a tu profesor por otras vías.\n\n"
            "¡Gracias por tu interés!"
        )
        return
    
    if query.data == "soy_profesor":
        await query.edit_message_text(
            "🔐 Para verificar tu identidad como profesor, "
            "por favor ingresa la contraseña:"
        )
        context.user_data['esperando_password'] = True

async def verificar_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica la contraseña ingresada"""
    password_ingresado = update.message.text.strip()
    password_correcto = Config.PROFESOR_PASSWORD
    user = update.effective_user
    db = context.bot_data['db']
    
    if password_ingresado == password_correcto:
        db.verificar_profesor(user.id)
        context.user_data['esperando_password'] = False
        
        await update.message.reply_text(
            "✅ *¡Acceso validado correctamente!*\n\n"
            "Bienvenido al *Delegado Virtual*, tu asistente para gestionar "
            "la comunicación con tus estudiantes de manera fácil y eficiente.\n\n"
            "🎯 *Funcionalidades principales:*\n"
            "• Enviar anuncios y material de estudio\n"
            "• Gestionar recaudaciones\n"
            "• Redactar minutas formales\n"
            "• Control de asistencia y strikes\n"
            "• Buzón de asesoría\n"
            "• Y mucho más...\n\n"
            "💡 *Modo de uso:*\n"
            "• Escribe /menu para ver todas las opciones\n"
            "• O simplemente dime qué necesitas y yo te ayudo\n\n"
            "¡Comencemos! 🚀",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Contraseña incorrecta. No se puede validar tu acceso como profesor.\n\n"
            "Si eres profesor de la UDO Monagas y no conoces la contraseña, "
            "por favor contacta al administrador del sistema."
        )
        context.user_data['esperando_password'] = False
