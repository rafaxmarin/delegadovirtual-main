from telegram import Update
from telegram.ext import ContextTypes
from src.presentation.keyboards import get_menu_keyboard

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /menu"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text(
            "🔒 Debes verificar tu acceso de profesor primero. Usa /start para comenzar."
        )
        return
    
    await update.message.reply_text(
        "📋 *MENÚ PRINCIPAL - Delegado Virtual*\n\n"
        "Selecciona la función que deseas utilizar:",
        parse_mode='Markdown',
        reply_markup=get_menu_keyboard()
    )

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde un callback button"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📋 *MENÚ PRINCIPAL - Delegado Virtual*\n\n"
        "Selecciona la función que deseas utilizar:",
        parse_mode='Markdown',
        reply_markup=get_menu_keyboard()
    )
