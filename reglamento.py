from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gemini_handler import GeminiHandler
from telegram.error import TelegramError

async def fijar_reglamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para fijar reglamento"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_reglamento'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📜 *FIJAR REGLAMENTO*\n\n"
        "Envíame las normas de convivencia que deseas establecer.\n"
        "Puede ser un mensaje de texto o una nota de voz.\n\n"
        "Yo lo estructuraré de manera formal y lo fijaré en el grupo "
        "para que todos los estudiantes puedan verlo.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_reglamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el reglamento del profesor"""
    if not context.user_data.get('esperando_reglamento'):
        return
    
    reglamento = None
    
    if update.message.text:
        reglamento = update.message.text
    elif update.message.voice:
        await update.message.reply_text(
            "🎙️ Nota de voz recibida. Por favor, envía el reglamento como texto "
            "para asegurar la precisión del contenido."
        )
        return
    
    if not reglamento:
        return
    
    # Estructurar con Gemini
    await update.message.reply_text("✨ Estructurando reglamento formal...")
    
    try:
        reglamento_formal = GeminiHandler.estructurar_texto_formal(
            f"Convierte el siguiente contenido en un reglamento o normas de convivencia "
            f"para un grupo universitario. Usa un tono formal y enumera las reglas:\n\n{reglamento}"
        )
    except Exception as e:
        await update.message.reply_text("❌ Error al procesar el reglamento. Intenta de nuevo.")
        return
    
    context.user_data['reglamento_formal'] = reglamento_formal
    context.user_data['esperando_reglamento'] = False
    
    # Mostrar vista previa
    keyboard = [
        [
            InlineKeyboardButton("✅ Continuar", callback_data="confirmar_reglamento"),
            InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📜 *VISTA PREVIA DEL REGLAMENTO:*\n\n"
        f"{reglamento_formal}\n\n"
        "¿Deseas fijar este reglamento?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def confirmar_reglamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma y pregunta a qué grupo(s) aplicar el reglamento"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    if not context.user_data.get('reglamento_formal'):
        await query.edit_message_text("❌ No hay reglamento para fijar.")
        return
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"fijar_reglamento_{chat_id}")])
    keyboard.append([InlineKeyboardButton("📚 Todos los grupos", callback_data="fijar_reglamento_todos")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 ¿A qué grupo deseas fijar el reglamento?",
        reply_markup=reply_markup
    )

async def fijar_reglamento_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fija el reglamento en el grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    reglamento = context.user_data.get('reglamento_formal')
    
    if not reglamento:
        await query.edit_message_text("❌ No hay reglamento para fijar.")
        return
    
    data = query.data
    
    if data == "fijar_reglamento_todos":
        # Fijar en todos los grupos
        grupos = db.obtener_grupos_profesor(user.id)
        exitosos = 0
        fallos = 0
        
        for chat_id, nombre in grupos:
            try:
                await fijar_en_grupo(context, chat_id, reglamento)
                exitosos += 1
            except Exception as e:
                fallos += 1
        
        await query.edit_message_text(
            f"✅ Reglamento fijado en {exitosos} grupo(s).\n"
            + (f"❌ Fallos: {fallos}" if fallos > 0 else "")
        )
    else:
        # Fijar en un grupo específico
        chat_id = int(data.replace("fijar_reglamento_", ""))
        
        try:
            await fijar_en_grupo(context, chat_id, reglamento)
            await query.edit_message_text("✅ Reglamento fijado exitosamente.")
        except Exception as e:
            await query.edit_message_text(f"❌ Error al fijar el reglamento: {str(e)}")
    
    # Limpiar contexto
    context.user_data.pop('reglamento_formal', None)

async def fijar_en_grupo(context, chat_id, reglamento):
    """Intenta fijar el reglamento en la descripción o como mensaje fijado"""
    mensaje_reglamento = f"📜 *NORMAS DE CONVIVENCIA*\n\n{reglamento}"
    
    try:
        # Opción 1: Intentar poner en la descripción del grupo
        await context.bot.set_chat_description(chat_id, reglamento[:255])  # Límite de Telegram
        return True
    except TelegramError:
        pass
    
    # Opción 2: Enviar como mensaje y fijarlo
    try:
        mensaje = await context.bot.send_message(
            chat_id,
            mensaje_reglamento,
            parse_mode='Markdown'
        )
        await context.bot.pin_chat_message(chat_id, mensaje.message_id)
        return True
    except TelegramError:
        # Si no se puede fijar, enviar mensaje normal
        await context.bot.send_message(
            chat_id,
            mensaje_reglamento,
            parse_mode='Markdown'
        )
        return True