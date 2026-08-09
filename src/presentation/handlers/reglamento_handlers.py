from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = GeminiAdapter()

async def fijar_reglamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para fijar reglamento"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_reglamento'] = True
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📜 *FIJAR REGLAMENTO*\n\n"
        "Envíame las normas de convivencia que deseas establecer.\n\n"
        "Yo lo estructuraré de manera formal y lo fijaré en el grupo.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_reglamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el reglamento del profesor"""
    if not context.user_data.get('esperando_reglamento'):
        return
    
    if not update.message or not update.message.text:
        return
    
    reglamento = update.message.text
    await update.message.reply_text("✨ Estructurando reglamento formal...")
    
    try:
        reglamento_formal = gemini.estructurar_texto_formal(
            f"Convierte el siguiente contenido en un reglamento o normas de convivencia "
            f"para un grupo universitario. Usa un tono formal y enumera las reglas:\n\n{reglamento}"
        )
    except Exception:
        reglamento_formal = reglamento
    
    context.user_data['reglamento_formal'] = reglamento_formal
    context.user_data['esperando_reglamento'] = False
    
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
        grupos = db.obtener_grupos_profesor(user.id)
        exitosos = 0
        fallos = 0
        
        for chat_id, nombre in grupos:
            try:
                await fijar_en_grupo(context, chat_id, reglamento)
                exitosos += 1
            except Exception:
                fallos += 1
        
        await query.edit_message_text(
            f"✅ Reglamento fijado en {exitosos} grupo(s).\n"
            + (f"❌ Fallos: {fallos}" if fallos > 0 else "")
        )
    else:
        chat_id = int(data.replace("fijar_reglamento_", ""))
        if not await verificar_pertenencia_grupo(chat_id, user.id, db, query):
            return
        try:
            await fijar_en_grupo(context, chat_id, reglamento)
            await query.edit_message_text("✅ Reglamento fijado exitosamente.")
        except Exception as e:
            await query.edit_message_text(f"❌ Error al fijar el reglamento: {str(e)}")
    
    context.user_data.pop('reglamento_formal', None)

async def fijar_en_grupo(context, chat_id, reglamento):
    """Intenta fijar el reglamento"""
    mensaje_reglamento = f"📜 *NORMAS DE CONVIVENCIA*\n\n{reglamento}"
    try:
        mensaje = await context.bot.send_message(chat_id, mensaje_reglamento, parse_mode='Markdown')
        await context.bot.pin_chat_message(chat_id, mensaje.message_id)
        return True
    except TelegramError:
        return True
