from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = GeminiAdapter()

async def emitir_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para emitir un anuncio"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_anuncio'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 *EMITIR ANUNCIO*\n\n"
        "Envíame el mensaje que deseas comunicar a tus estudiantes.\n"
        "Puede ser un mensaje de texto o una nota de voz.\n\n"
        "Yo lo estructuraré de manera formal y respetuosa.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el anuncio del profesor (texto o voz)"""
    if not context.user_data.get('esperando_anuncio'):
        return
    
    if not update.message:
        return
    
    anuncio_original = None
    if update.message.text:
        anuncio_original = update.message.text
    elif update.message.voice:
        await update.message.reply_text(
            "Por favor, envía el anuncio como mensaje de texto por ahora. "
            "La transcripción directa de voz estará disponible próximamente."
        )
        return
    
    if not anuncio_original:
        return
    
    await update.message.reply_text("✨ Estructurando anuncio formal...")
    
    try:
        anuncio_formal = gemini.estructurar_texto_formal(anuncio_original)
    except Exception:
        anuncio_formal = anuncio_original
    
    context.user_data['anuncio_formal'] = anuncio_formal
    context.user_data['esperando_anuncio'] = False
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Enviar", callback_data="confirmar_anuncio"),
            InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📢 *VISTA PREVIA DEL ANUNCIO:*\n\n"
        f"{anuncio_formal}\n\n"
        "¿Deseas enviar este anuncio?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def confirmar_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma y envía el anuncio al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    anuncio_formal = context.user_data.get('anuncio_formal')
    if not anuncio_formal:
        await query.edit_message_text("❌ No hay anuncio para enviar.")
        return
    
    grupos = db.obtener_grupos_profesor(user.id)
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"enviar_anuncio_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 ¿A qué grupo deseas enviar el anuncio?",
        reply_markup=reply_markup
    )

async def enviar_anuncio_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el anuncio al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("enviar_anuncio_", ""))
    anuncio_formal = context.user_data.get('anuncio_formal')
    db = context.bot_data['db']

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return
    
    if not anuncio_formal:
        await query.edit_message_text("❌ No hay anuncio para enviar.")
        return
    
    try:
        msg = await context.bot.send_message(
            chat_id,
            f"📢 *ANUNCIO OFICIAL*\n\n{anuncio_formal}",
            parse_mode='Markdown'
        )
        try: await context.bot.pin_chat_message(chat_id, msg.message_id)
        except Exception: pass
        
        await query.edit_message_text("✅ Anuncio enviado exitosamente.")
        context.user_data.pop('anuncio_formal', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar el anuncio: {str(e)}")
