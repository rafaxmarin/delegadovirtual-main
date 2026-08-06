from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.gemini_adapter import GeminiAdapter

gemini = GeminiAdapter()

async def buzon_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el buzón de asesoría al profesor"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    solicitudes = db.obtener_asesorias_pendientes(user.id)
    
    if not solicitudes:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📬 *BUZÓN DE ASESORÍA*\n\n"
            "No tienes solicitudes pendientes.\n\n"
            "Los estudiantes pueden etiquetar al bot en el grupo "
            "para hacer preguntas que te llegarán aquí.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    mensaje = "📬 *BUZÓN DE ASESORÍA - Solicitudes pendientes*\n\n"
    keyboard = []
    for solicitud_id, grupo_nombre, estudiante, pregunta in solicitudes:
        mensaje += (
            f"📚 *{grupo_nombre}*\n"
            f"👤 {estudiante}\n"
            f"💬 {pregunta}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(
                f"✅ Responder a {estudiante}",
                callback_data=f"responder_asesoria_{solicitud_id}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Ignorar",
                callback_data=f"ignorar_asesoria_{solicitud_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def responder_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prepara la respuesta a una solicitud de asesoría"""
    query = update.callback_query
    await query.answer()
    
    solicitud_id = int(query.data.replace("responder_asesoria_", ""))
    db = context.bot_data['db']
    
    solicitudes = db.obtener_asesorias_pendientes(query.from_user.id)
    solicitud = next((s for s in solicitudes if s[0] == solicitud_id), None)
    
    if not solicitud:
        await query.edit_message_text("❌ Solicitud no encontrada.")
        return
    
    context.user_data['respondiendo_asesoria'] = solicitud_id
    context.user_data['asesoria_grupo'] = solicitud[1]
    context.user_data['asesoria_estudiante'] = solicitud[2]
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💬 *Responder a {solicitud[2]}*\n\n"
        f"Pregunta: {solicitud[3]}\n\n"
        "Escribe tu respuesta (texto o nota de voz).\n"
        "El bot la estructurará de manera formal.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_respuesta_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y envía la respuesta del profesor"""
    if not context.user_data.get('respondiendo_asesoria'):
        return
    
    respuesta = update.message.text
    if not respuesta:
        return
    
    solicitud_id = context.user_data.get('respondiendo_asesoria')
    grupo_nombre = context.user_data.get('asesoria_grupo')
    estudiante = context.user_data.get('asesoria_estudiante')
    db = context.bot_data['db']
    
    try:
        respuesta_formal = gemini.estructurar_texto_formal(respuesta)
    except Exception:
        respuesta_formal = respuesta
    
    try:
        grupos = db.obtener_grupos_profesor(update.effective_user.id)
        grupo_id = next((chat_id for chat_id, nombre in grupos if nombre == grupo_nombre), None)
        
        if grupo_id:
            await context.bot.send_message(
                grupo_id,
                f"💬 *RESPUESTA DEL PROFESOR*\n\n"
                f"👤 Para: {estudiante}\n\n"
                f"{respuesta_formal}",
                parse_mode='Markdown'
            )
            db.marcar_asesoria_respondida(solicitud_id)
            await update.message.reply_text(f"✅ Respuesta enviada a {estudiante} en {grupo_nombre}.")
        else:
            await update.message.reply_text("❌ No se encontró el grupo.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar la respuesta: {str(e)}")
    
    context.user_data.pop('respondiendo_asesoria', None)
    context.user_data.pop('asesoria_grupo', None)
    context.user_data.pop('asesoria_estudiante', None)

async def ignorar_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora una solicitud de asesoría"""
    query = update.callback_query
    await query.answer()
    
    solicitud_id = int(query.data.replace("ignorar_asesoria_", ""))
    db = context.bot_data['db']
    
    db.marcar_asesoria_respondida(solicitud_id)
    await query.edit_message_text("✅ Solicitud ignorada.")
    await buzon_asesoria(update, context)


async def detectar_solicitud_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando un estudiante etiqueta al bot en un grupo (CORREGIDO ES_GRUPO_REGISTRADO)"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if chat.type not in ['group', 'supergroup']:
        return
    
    if not message or not message.text:
        return
    
    bot_username = context.bot.username
    if f"@{bot_username}" not in message.text:
        return
    
    # 🔴 CORRECCIÓN: Verificar registro de grupo adecuadamente
    if not db.es_grupo_registrado(chat.id):
        return
    
    contador = db.obtener_contador_asesorias(chat.id)
    if contador >= 10:
        await message.reply_text("❌ Se ha alcanzado el límite de 10 solicitudes por hoy. Intenta de nuevo mañana.")
        return
    
    pregunta = message.text.replace(f"@{bot_username}", "").strip()
    if not pregunta:
        await message.reply_text("Por favor, escribe tu pregunta después de etiquetarme.")
        return
    
    db.agregar_asesoria(chat.id, chat.title or "Grupo", user.full_name, pregunta)
    db.incrementar_contador_asesorias(chat.id)
    
    await message.reply_text(
        f"✅ Tu pregunta ha sido enviada al profesor.\n"
        f"Solicitudes hoy: {contador + 1}/10"
    )

async def enviar_recordatorio_asesoria(context: ContextTypes.DEFAULT_TYPE):
    """Envía recordatorio cada 48 horas a los grupos registrados"""
    db = context.bot_data['db']
    grupos = db.obtener_todos_los_grupos()
    
    for chat_id, _ in grupos:
        try:
            await context.bot.send_message(
                chat_id,
                "📬 *BUZÓN DE ASESORÍA*\n\n"
                "Recuerda que puedes etiquetarme seguido de tu pregunta y se la haré llegar al profesor.\n\n"
                "⏰ Límite: 10 solicitudes por grupo cada 24 horas.",
                parse_mode='Markdown'
            )
        except Exception:
            pass
