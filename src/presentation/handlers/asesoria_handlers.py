from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.ai_service import AIService
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = AIService()

async def buzon_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el buzón de asesoría al profesor"""
    user = update.effective_user
    db = context.bot_data['db']

    if update.callback_query:
        await update.callback_query.answer()
    
    solicitudes = db.obtener_asesorias_pendientes(user.id)
    
    if not solicitudes:
        mensaje = "📬 *BUZÓN DE ASESORÍA*\n\n✅ No tienes solicitudes de asesoría pendientes."
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    mensaje = f"📬 *BUZÓN DE ASESORÍA - Solicitudes pendientes ({len(solicitudes)})*\n\n"
    keyboard = []
    for sol in solicitudes:
        solicitud_id = sol[0]
        grupo_nombre = sol[1]
        estudiante = sol[2]
        pregunta = sol[3]
        
        mensaje += (
            f"📚 *{grupo_nombre}*\n"
            f"👤 *{estudiante}*\n"
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
                f"❌ Ignorar a {estudiante}",
                callback_data=f"ignorar_asesoria_{solicitud_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)

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
    context.user_data['asesoria_pregunta'] = solicitud[3]
    context.user_data['asesoria_grupo_id'] = solicitud[4] if len(solicitud) > 4 else None
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💬 *Responder a {solicitud[2]}*\n\n"
        f"❓ *Pregunta:* \"{solicitud[3]}\"\n\n"
        "Escribe la respuesta que deseas enviar a tu estudiante.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_respuesta_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y envía la respuesta exacta del profesor al grupo"""
    if not context.user_data.get('respondiendo_asesoria'):
        return
    
    if not update.message or not update.message.text:
        return
    
    respuesta_profesor = update.message.text.strip()
    solicitud_id = context.user_data.get('respondiendo_asesoria')
    grupo_nombre = context.user_data.get('asesoria_grupo')
    estudiante = context.user_data.get('asesoria_estudiante')
    pregunta = context.user_data.get('asesoria_pregunta', '')
    grupo_id = context.user_data.get('asesoria_grupo_id')
    db = context.bot_data['db']
    
    if not grupo_id:
        grupos = db.obtener_grupos_profesor(update.effective_user.id)
        grupo_id = next((chat_id for chat_id, nombre in grupos if nombre == grupo_nombre), None)
    
    if not grupo_id:
        await update.message.reply_text("❌ No se encontró el grupo correspondiente.")
        return
    
    try:
        await context.bot.send_message(
            grupo_id,
            f"💬 *RESPUESTA DE ASESORÍA DEL PROFESOR*\n\n"
            f"👤 *Para:* {estudiante}\n"
            f"❓ *Pregunta:* \"{pregunta}\"\n\n"
            f"✍️ *Respuesta:* {respuesta_profesor}",
            parse_mode='Markdown'
        )
        
        db.marcar_asesoria_respondida(solicitud_id)
        await update.message.reply_text(f"✅ Respuesta enviada exitosamente a {estudiante} en {grupo_nombre}.")
        
        # Reabrir el buzón de asesoría automáticamente para listar las demás preguntas
        await buzon_asesoria(update, context)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar la respuesta al grupo: {str(e)}")
    
    context.user_data.pop('respondiendo_asesoria', None)
    context.user_data.pop('asesoria_grupo', None)
    context.user_data.pop('asesoria_estudiante', None)
    context.user_data.pop('asesoria_pregunta', None)
    context.user_data.pop('asesoria_grupo_id', None)

async def ignorar_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora una solicitud de asesoría"""
    query = update.callback_query
    await query.answer("Solicitud ignorada.")
    
    solicitud_id = int(query.data.replace("ignorar_asesoria_", ""))
    db = context.bot_data['db']

    # Verificar que la asesoría pertenezca al profesor
    solicitudes = db.obtener_asesorias_pendientes(query.from_user.id)
    solicitud = next((s for s in solicitudes if s[0] == solicitud_id), None)
    if not solicitud:
        await query.edit_message_text("❌ No tienes permisos sobre esta solicitud.")
        return

    db.marcar_asesoria_respondida(solicitud_id)
    await buzon_asesoria(update, context)


async def notificar_profesor_nueva_asesoria(
    context: ContextTypes.DEFAULT_TYPE,
    profesor_id: int,
    grupo_nombre: str,
    estudiante_nombre: str,
    pregunta: str,
    solicitud_id: int = None
):
    """Envía una notificación privada inmediata al profesor con botones interactivos"""
    if not profesor_id:
        return
    
    mensaje = (
        f"📬 *NUEVA SOLICITUD DE ASESORÍA*\n\n"
        f"📚 *Grupo:* {grupo_nombre}\n"
        f"👤 *Estudiante:* {estudiante_nombre}\n"
        f"💬 *Pregunta:* \"{pregunta}\"\n\n"
        f"💡 Puedes responder de inmediato usando los botones de abajo o accediendo al buzón."
    )
    
    keyboard = []
    if solicitud_id:
        keyboard.append([
            InlineKeyboardButton(
                f"💬 Responder a {estudiante_nombre}",
                callback_data=f"responder_asesoria_{solicitud_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("📬 Abrir Buzón de Asesoría", callback_data="menu_asesoria")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=profesor_id,
            text=mensaje,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        print(f"🔔 Notificación privada interactiva enviada con éxito al profesor ID {profesor_id}")
    except Exception as e:
        print(f"❌ No se pudo enviar notificación privada al profesor ID {profesor_id}: {e}")

async def enviar_pregunta_asesoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el comando /pregunta enviado por un estudiante en un grupo"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']

    if chat.type not in ['group', 'supergroup']:
        await message.reply_text("ℹ️ El comando /pregunta se utiliza dentro de un grupo de clase.")
        return

    if not db.es_grupo_registrado(chat.id):
        print(f"⚠️ El grupo '{chat.title}' (ID: {chat.id}) NO está registrado en la base de datos.")
        await message.reply_text(
            "⚠️ Este grupo aún no está registrado por ningún profesor.\n"
            "El profesor debe invitar al bot y confirmar el registro por mensaje privado."
        )
        return

    pregunta = " ".join(context.args).strip() if context.args else ""
    if not pregunta and message and message.text:
        partes = message.text.split(maxsplit=1)
        if len(partes) > 1:
            pregunta = partes[1].strip()

    if not pregunta:
        await message.reply_text(
            "❓ *¿Cómo hacer una pregunta al profesor?*\n\n"
            "Escribe el comando `/pregunta` seguido de tu duda.\n\n"
            "Ejemplo:\n"
            "`/pregunta ¿Cuándo es la fecha de entrega del examen final?`",
            parse_mode='Markdown'
        )
        return

    contador = db.obtener_contador_asesorias(chat.id)
    if contador >= 10:
        await message.reply_text("❌ Se ha alcanzado el límite de 10 solicitudes por hoy. Intenta de nuevo mañana.")
        return

    solicitud_id = db.agregar_asesoria(chat.id, chat.title or "Grupo", user.full_name, pregunta)
    db.incrementar_contador_asesorias(chat.id)
    print(f"✅ Asesoría recibida vía /pregunta (ID: {solicitud_id}): '{pregunta}' en grupo '{chat.title}'")

    await message.reply_text(
        f"✅ Tu pregunta ha sido enviada al profesor.\n"
        f"Solicitudes hoy: {contador + 1}/10"
    )

    profesor_id = db.obtener_profesor_de_grupo(chat.id)
    if profesor_id:
        await notificar_profesor_nueva_asesoria(
            context=context,
            profesor_id=profesor_id,
            grupo_nombre=chat.title or "Grupo",
            estudiante_nombre=user.full_name,
            pregunta=pregunta,
            solicitud_id=solicitud_id
        )

async def detectar_solicitud_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando un estudiante etiqueta al bot en un grupo y notifica al profesor"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if chat.type not in ['group', 'supergroup']:
        return
    
    if not message or not message.text:
        return
    
    bot_username = context.bot.username
    if not bot_username:
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as e:
            print(f"⚠️ No se pudo obtener el username del bot: {e}")
            return
    
    # Búsqueda insensible a mayúsculas/minúsculas del @bot_username
    if f"@{bot_username}".lower() not in message.text.lower():
        from src.presentation.handlers.strike_handlers import monitorear_mensajes
        await monitorear_mensajes(update, context)
        return
    
    print(f"📩 Detectada mención a @{bot_username} en grupo '{chat.title}' (ID: {chat.id}) por {user.full_name}")

    if not db.es_grupo_registrado(chat.id):
        print(f"⚠️ El grupo '{chat.title}' (ID: {chat.id}) NO está registrado en la base de datos.")
        await message.reply_text(
            "⚠️ Este grupo aún no está registrado por ningún profesor.\n"
            "El profesor debe invitar al bot y confirmar el registro por mensaje privado."
        )
        return
    
    contador = db.obtener_contador_asesorias(chat.id)
    if contador >= 10:
        await message.reply_text("❌ Se ha alcanzado el límite de 10 solicitudes por hoy. Intenta de nuevo mañana.")
        return
    
    # Remover la mención del bot sin importar mayúsculas/minúsculas
    import re
    pregunta = re.sub(re.escape(f"@{bot_username}"), "", message.text, flags=re.IGNORECASE).strip()
    if not pregunta:
        await message.reply_text("Por favor, escribe tu pregunta después de etiquetarme o usa /pregunta.")
        return
    
    solicitud_id = db.agregar_asesoria(chat.id, chat.title or "Grupo", user.full_name, pregunta)
    db.incrementar_contador_asesorias(chat.id)
    print(f"✅ Asesoría guardada exitosamente en DB (ID: {solicitud_id}): '{pregunta}' para el grupo '{chat.title}'")
    
    await message.reply_text(
        f"✅ Tu pregunta ha sido enviada al profesor.\n"
        f"Solicitudes hoy: {contador + 1}/10"
    )
    
    # 🔔 NOTIFICACIÓN INSTANTÁNEA PRIVADA AL PROFESOR
    profesor_id = db.obtener_profesor_de_grupo(chat.id)
    if profesor_id:
        await notificar_profesor_nueva_asesoria(
            context=context,
            profesor_id=profesor_id,
            grupo_nombre=chat.title or "Grupo",
            estudiante_nombre=user.full_name,
            pregunta=pregunta,
            solicitud_id=solicitud_id
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
