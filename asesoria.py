from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import asyncio

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
        # Truncar pregunta si es muy larga
        pregunta_corta = pregunta[:50] + "..." if len(pregunta) > 50 else pregunta
        
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
    
    # Obtener datos de la solicitud
    solicitudes = db.obtener_asesorias_pendientes(query.from_user.id)
    solicitud = None
    for s in solicitudes:
        if s[0] == solicitud_id:
            solicitud = s
            break
    
    if not solicitud:
        await query.edit_message_text("❌ Solicitud no encontrada.")
        return
    
    context.user_data['respondiendo_asesoria'] = solicitud_id
    context.user_data['asesoria_grupo'] = solicitud[1]
    context.user_data['asesoria_estudiante'] = solicitud[2]
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="menu_asesoria")]]
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
    
    respuesta = None
    
    if update.message.text:
        respuesta = update.message.text
    elif update.message.voice:
        await update.message.reply_text(
            "🎙️ Nota de voz recibida. Por favor, envía la respuesta como texto."
        )
        return
    
    if not respuesta:
        return
    
    solicitud_id = context.user_data.get('respondiendo_asesoria')
    grupo_nombre = context.user_data.get('asesoria_grupo')
    estudiante = context.user_data.get('asesoria_estudiante')
    db = context.bot_data['db']
    
    # Estructurar respuesta con Gemini
    try:
        from gemini_handler import GeminiHandler
        respuesta_formal = GeminiHandler.estructurar_texto_formal(respuesta)
    except:
        respuesta_formal = respuesta
    
    # Enviar al grupo
    try:
        # Buscar el grupo por nombre
        grupos = db.obtener_grupos_profesor(update.effective_user.id)
        grupo_id = None
        for chat_id, nombre in grupos:
            if nombre == grupo_nombre:
                grupo_id = chat_id
                break
        
        if grupo_id:
            await context.bot.send_message(
                grupo_id,
                f"💬 *RESPUESTA DEL PROFESOR*\n\n"
                f"👤 Para: {estudiante}\n\n"
                f"{respuesta_formal}",
                parse_mode='Markdown'
            )
            
            # Marcar como respondida
            db.marcar_asesoria_respondida(solicitud_id)
            
            await update.message.reply_text(
                f"✅ Respuesta enviada a {estudiante} en {grupo_nombre}."
            )
        else:
            await update.message.reply_text("❌ No se encontró el grupo.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar la respuesta: {str(e)}")
    
    # Limpiar contexto
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
    
    # Volver al buzón
    await buzon_asesoria(update, context)

async def detectar_solicitud_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando un estudiante etiqueta al bot en un grupo"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    # Solo en grupos
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Verificar si el mensaje etiqueta al bot
    bot_username = context.bot.username
    if not message.text or f"@{bot_username}" not in message.text:
        return
    
    # Verificar si es un grupo registrado
    grupos = db.obtener_grupos_profesor(None)  # Obtener todos los grupos
    grupo_registrado = False
    profesor_id = None
    for chat_id, nombre in grupos:
        if chat_id == chat.id:
            grupo_registrado = True
            # Obtener profesor_id
            import sqlite3
            conn = db.conn
            cursor = conn.cursor()
            cursor.execute('SELECT profesor_id FROM grupos WHERE chat_id = ?', (chat.id,))
            result = cursor.fetchone()
            if result:
                profesor_id = result[0]
            break
    
    if not grupo_registrado:
        return
    
    # Verificar límite diario (10 solicitudes por grupo)
    contador = db.obtener_contador_asesorias(chat.id)
    
    if contador >= 10:
        await message.reply_text(
            "❌ Se ha alcanzado el límite de 10 solicitudes por hoy. "
            "Intenta de nuevo mañana."
        )
        return
    
    # Extraer pregunta (eliminar etiqueta del bot)
    pregunta = message.text.replace(f"@{bot_username}", "").strip()
    
    if not pregunta:
        await message.reply_text(
            "Por favor, escribe tu pregunta después de etiquetarme."
        )
        return
    
    # Registrar solicitud
    db.agregar_asesoria(chat.id, chat.title, user.full_name, pregunta)
    db.incrementar_contador_asesorias(chat.id)
    
    # Confirmar al estudiante
    await message.reply_text(
        f"✅ Tu pregunta ha sido enviada al profesor.\n"
        f"Solicitudes hoy: {contador + 1}/10"
    )
    
    # Notificar al profesor si está disponible
    if profesor_id:
        try:
            await context.bot.send_message(
                profesor_id,
                f"📬 *NUEVA SOLICITUD DE ASESORÍA*\n\n"
                f"Grupo: {chat.title}\n"
                f"Estudiante: {user.full_name}\n"
                f"Pregunta: {pregunta}\n\n"
                f"Revisa el buzón de asesoría en /menu",
                parse_mode='Markdown'
            )
        except:
            pass

async def enviar_recordatorio_asesoria(context: ContextTypes.DEFAULT_TYPE):
    """Envía recordatorio cada 48 horas a los grupos sobre el buzón de asesoría"""
    db = context.bot_data['db']
    
    # Obtener todos los grupos registrados
    cursor = db.conn.cursor()
    cursor.execute('SELECT DISTINCT chat_id FROM grupos')
    grupos = cursor.fetchall()
    
    for (chat_id,) in grupos:
        try:
            await context.bot.send_message(
                chat_id,
                "📬 *BUZÓN DE ASESORÍA*\n\n"
                "Recuerda que puedes etiquetarme (@DelegadoVirtual) "
                "seguido de tu pregunta y se la haré llegar al profesor.\n\n"
                "⏰ Límite: 10 solicitudes por grupo cada 24 horas.",
                parse_mode='Markdown'
            )
        except:
            pass