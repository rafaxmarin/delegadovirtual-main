from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Despliega el menú principal con botones"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text(
            "Primero debes validar tu acceso. Usa /start para comenzar."
        )
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Estado de grupos", callback_data="menu_estado_grupos"),
            InlineKeyboardButton("💰 Recaudación", callback_data="menu_recaudacion")
        ],
        [
            InlineKeyboardButton("📢 Emitir anuncio", callback_data="menu_anuncio"),
            InlineKeyboardButton("📝 Redactar minuta", callback_data="menu_minuta")
        ],
        [
            InlineKeyboardButton("📚 Compartir material", callback_data="menu_material"),
            InlineKeyboardButton("📬 Buzón de asesoría", callback_data="menu_asesoria")
        ],
        [
            InlineKeyboardButton("⚡ Control de strikes", callback_data="menu_strikes"),
            InlineKeyboardButton("📜 Fijar reglamento", callback_data="menu_reglamento")
        ],
        [
            InlineKeyboardButton("➕ Agregar alumno", callback_data="menu_agregar"),
            InlineKeyboardButton("➖ Eliminar alumno", callback_data="menu_eliminar")
        ],
        [
            InlineKeyboardButton("❌ Cerrar panel", callback_data="menu_cerrar")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 *MENÚ PRINCIPAL - Delegado Virtual*\n\n"
        "Selecciona la función que deseas utilizar:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )