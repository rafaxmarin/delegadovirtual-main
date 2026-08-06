from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from gemini_handler import GeminiHandler

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
    
    user = update.effective_user
    db = context.bot_data['db']
    anuncio_original = None
    
    # Verificar si es texto
    if update.message.text:
        anuncio_original = update.message.text
    
    # Verificar si es nota de voz
    elif update.message.voice:
        await update.message.reply_text("🎙️ Procesando nota de voz...")
        # Transcribir con Gemini (usamos el archivo de voz)
        file = await update.message.voice.get_file()
        # Nota: La transcripción directa de audio requiere implementación adicional
        # Por ahora, usamos el mensaje de texto asociado o pedimos texto
        await update.message.reply_text(
            "Por favor, envía el anuncio como mensaje de texto. "
            "La transcripción de voz estará disponible en una próxima actualización."
        )
        return
    
    if not anuncio_original:
        return
    
    # Estructurar con Gemini
    await update.message.reply_text("✨ Estructurando anuncio formal...")
    
    try:
        anuncio_formal = GeminiHandler.estructurar_texto_formal(anuncio_original)
    except Exception as e:
        await update.message.reply_text(
            "❌ Error al procesar el anuncio. Intenta de nuevo."
        )
        return
    
    # Guardar en contexto
    context.user_data['anuncio_formal'] = anuncio_formal
    context.user_data['esperando_anuncio'] = False
    
    # Mostrar vista previa
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
    
    # Obtener grupos del profesor
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text(
            "❌ No tienes grupos registrados. Agrega el bot a un grupo primero."
        )
        return
    
    # Mostrar grupos para seleccionar
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
    
    if not anuncio_formal:
        await query.edit_message_text("❌ No hay anuncio para enviar.")
        return
    
    try:
        await context.bot.send_message(
            chat_id,
            f"📢 *ANUNCIO OFICIAL*\n\n{anuncio_formal}",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text("✅ Anuncio enviado exitosamente.")
        
        # Limpiar contexto
        context.user_data.pop('anuncio_formal', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar el anuncio: {str(e)}")