from telegram import Update
from telegram.ext import ContextTypes
from src.presentation.keyboards import get_menu_keyboard

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /menu y despliega el menú principal (Soporta callback y message)"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not db.es_profesor_verificado(user.id):
        texto_error = "🔒 Debes verificar tu acceso de profesor primero. Usa /start para comenzar."
        if update.callback_query:
            await update.callback_query.message.reply_text(texto_error)
        elif update.message:
            await update.message.reply_text(texto_error)
        return
    
    texto_menu = (
        "📋 *MENÚ PRINCIPAL - Delegado Virtual*\n\n"
        "Selecciona la función que deseas utilizar:"
    )
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                texto_menu,
                parse_mode='Markdown',
                reply_markup=get_menu_keyboard()
            )
        except Exception:
            await update.callback_query.message.reply_text(
                texto_menu,
                parse_mode='Markdown',
                reply_markup=get_menu_keyboard()
            )
    elif update.message:
        await update.message.reply_text(
            texto_menu,
            parse_mode='Markdown',
            reply_markup=get_menu_keyboard()
        )

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde un callback button y limpia el estado activo"""
    await menu(update, context)
