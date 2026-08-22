from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.ai_service import AIService
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = AIService()

async def emitir_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para emitir un anuncio"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_anuncio'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 *EMITIR ANUNCIO*\n\n"
        "Envíame la información o archivo que deseas comunicar a tus estudiantes.\n\n"
        "Puedes enviar:\n"
        "• Mensaje de texto o nota de voz (la IA la procesará)\n"
        "• Documentos de cualquier formato (PDF, Word, Excel, ZIP, etc.) con su descripción\n"
        "• Fotos, videos, audios, animaciones o stickers\n\n"
        "Yo lo estructuraré de manera formal y respetuosa.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el anuncio del profesor (texto, voz procesada por IA, documentos de cualquier tipo o medios de Telegram)"""
    if not context.user_data.get('esperando_anuncio'):
        return
    
    if not update.message:
        return
    
    msg = update.message
    anuncio_original = None
    anuncio_media = None
    tipo_anuncio_media = None
    desc_medio = None
    anuncio_formal = None

    if msg.voice:
        anuncio_media = msg.voice
        tipo_anuncio_media = 'voz'
        desc_medio = "🎙️ Nota de voz (procesada por IA)"
        await msg.reply_text("🎙️ Procesando nota de voz con IA...")
        try:
            file_obj = await context.bot.get_file(msg.voice.file_id)
            audio_bytes = await file_obj.download_as_bytearray()
            anuncio_formal = gemini.procesar_nota_voz_anuncio(bytes(audio_bytes), mime_type="audio/ogg")
        except Exception as e:
            await msg.reply_text(f"❌ Error al procesar la nota de voz con IA: {str(e)}")
            return

    elif msg.audio:
        anuncio_media = msg.audio
        tipo_anuncio_media = 'audio'
        desc_medio = "🎵 Archivo de audio (procesado por IA)"
        await msg.reply_text("🎵 Procesando audio con IA...")
        try:
            file_obj = await context.bot.get_file(msg.audio.file_id)
            audio_bytes = await file_obj.download_as_bytearray()
            mime = msg.audio.mime_type or "audio/mp3"
            anuncio_formal = gemini.procesar_nota_voz_anuncio(bytes(audio_bytes), mime_type=mime)
        except Exception:
            anuncio_original = msg.caption or "Archivo de audio adjunto"

    elif msg.document:
        anuncio_media = msg.document
        tipo_anuncio_media = 'documento'
        anuncio_original = msg.caption
        file_name = msg.document.file_name or "Archivo adjunto"
        desc_medio = f"📄 Documento adjunto: `{file_name}`"

    elif msg.photo:
        anuncio_media = msg.photo[-1]
        tipo_anuncio_media = 'foto'
        anuncio_original = msg.caption
        desc_medio = "🖼️ Imagen adjunta"

    elif msg.video:
        anuncio_media = msg.video
        tipo_anuncio_media = 'video'
        anuncio_original = msg.caption
        desc_medio = "🎥 Video adjunto"

    elif msg.video_note:
        anuncio_media = msg.video_note
        tipo_anuncio_media = 'videonota'
        anuncio_original = msg.caption
        desc_medio = "📹 Video nota adjunta"

    elif msg.animation:
        anuncio_media = msg.animation
        tipo_anuncio_media = 'animacion'
        anuncio_original = msg.caption
        desc_medio = "🎞️ GIF/Animación adjunta"

    elif msg.sticker:
        anuncio_media = msg.sticker
        tipo_anuncio_media = 'sticker'
        anuncio_original = msg.caption
        desc_medio = "🎨 Sticker adjunto"

    elif msg.text:
        anuncio_original = msg.text
        tipo_anuncio_media = 'texto'

    if not anuncio_formal:
        if anuncio_original:
            await msg.reply_text("✨ Estructurando anuncio formal...")
            try:
                anuncio_formal = gemini.estructurar_texto_formal(anuncio_original)
            except Exception:
                anuncio_formal = anuncio_original
        elif anuncio_media:
            anuncio_formal = "Documento/archivo adjunto compartido por el profesor."
        else:
            await msg.reply_text("❌ No se detectó ningún mensaje o archivo para el anuncio.")
            return

    context.user_data['anuncio_formal'] = anuncio_formal
    context.user_data['anuncio_media'] = anuncio_media
    context.user_data['tipo_anuncio_media'] = tipo_anuncio_media
    context.user_data['esperando_anuncio'] = False
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Enviar", callback_data="confirmar_anuncio"),
            InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto_preview = "📢 *VISTA PREVIA DEL ANUNCIO:*\n\n"
    if desc_medio:
        texto_preview += f"{desc_medio}\n\n"
    texto_preview += f"{anuncio_formal}\n\n¿Deseas enviar este anuncio?"

    await msg.reply_text(
        texto_preview,
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
    anuncio_media = context.user_data.get('anuncio_media')
    if not anuncio_formal and not anuncio_media:
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
    """Envía el anuncio (texto o multimedia/archivo) al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("enviar_anuncio_", ""))
    anuncio_formal = context.user_data.get('anuncio_formal', '')
    anuncio_media = context.user_data.get('anuncio_media')
    tipo_media = context.user_data.get('tipo_anuncio_media')
    db = context.bot_data['db']

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return
    
    if not anuncio_formal and not anuncio_media:
        await query.edit_message_text("❌ No hay anuncio para enviar.")
        return
    
    try:
        texto_completo = f"📢 *ANUNCIO OFICIAL*\n\n{anuncio_formal}"
        msg_enviado = None

        # Telegram limita las captions a 1024 caracteres
        usar_caption_separado = (tipo_media and tipo_media not in ['texto', None]) and len(texto_completo) > 1000

        if tipo_media == 'documento':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_document(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'foto':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_photo(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'video':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_video(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'audio':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_audio(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'voz':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_voice(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'animacion':
            caption_actual = None if usar_caption_separado else texto_completo
            msg_enviado = await context.bot.send_animation(chat_id, anuncio_media, caption=caption_actual, parse_mode='Markdown')
        elif tipo_media == 'videonota':
            msg_enviado = await context.bot.send_video_note(chat_id, anuncio_media)
            usar_caption_separado = True
        elif tipo_media == 'sticker':
            msg_enviado = await context.bot.send_sticker(chat_id, anuncio_media)
            usar_caption_separado = True
        else:
            msg_enviado = await context.bot.send_message(chat_id, texto_completo, parse_mode='Markdown')

        # Si el caption era muy largo o el tipo de medio no soporta caption directo
        if usar_caption_separado and anuncio_formal:
            msg_texto = await context.bot.send_message(chat_id, texto_completo, parse_mode='Markdown')
            if not msg_enviado:
                msg_enviado = msg_texto

        if msg_enviado:
            try:
                await context.bot.pin_chat_message(chat_id, msg_enviado.message_id)
            except Exception:
                pass
            
            # Guardar el anuncio en la base de datos
            media_id_str = str(anuncio_media) if anuncio_media else None
            db.guardar_anuncio(chat_id, anuncio_formal, tipo_media, media_id_str)
        
        await query.edit_message_text("✅ Anuncio enviado y fijado exitosamente.")
        context.user_data.pop('anuncio_formal', None)
        context.user_data.pop('anuncio_media', None)
        context.user_data.pop('tipo_anuncio_media', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar el anuncio: {str(e)}")

async def consultar_ultimo_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta y despliega el último anuncio publicado en el grupo (Comando /anuncio y Botón Menú)"""
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    db = context.bot_data['db']

    # Si se invoca desde chat privado, buscar el grupo activo del estudiante o profesor
    if chat_type == 'private':
        target_chat_id = None
        grupos = db.obtener_todos_los_grupos()
        for g_id, _ in grupos:
            try:
                member = await context.bot.get_chat_member(g_id, user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    target_chat_id = g_id
                    break
            except Exception:
                continue

        if not target_chat_id:
            msg_text = "⚠️ *No se encontró ningún grupo registrado asociado a tu cuenta.*"
            if update.callback_query:
                keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
                await update.callback_query.edit_message_text(msg_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            elif update.message:
                await update.message.reply_text(msg_text, parse_mode='Markdown')
            return
        
        chat_id = target_chat_id

    anuncio = db.obtener_ultimo_anuncio(chat_id)
    if not anuncio:
        msg_text = "⚠️ *No hay ningún anuncio registrado en la base de datos para este grupo.*"
        if update.callback_query:
            keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
            await update.callback_query.edit_message_text(msg_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        elif update.message:
            await update.message.reply_text(msg_text, parse_mode='Markdown')
        return

    texto, tipo_media, media_id, fecha_hora = anuncio
    contenido = f"📢 *ÚLTIMO ANUNCIO OFICIAL*\n📅 *Fecha:* {fecha_hora}\n\n{texto}"

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        
        await query.edit_message_text(contenido, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        if tipo_media and tipo_media != 'texto' and media_id:
            try:
                if tipo_media == 'documento':
                    await context.bot.send_document(query.message.chat_id, media_id)
                elif tipo_media == 'foto':
                    await context.bot.send_photo(query.message.chat_id, media_id)
                elif tipo_media == 'video':
                    await context.bot.send_video(query.message.chat_id, media_id)
                elif tipo_media == 'audio':
                    await context.bot.send_audio(query.message.chat_id, media_id)
                elif tipo_media == 'voz':
                    await context.bot.send_voice(query.message.chat_id, media_id)
            except Exception:
                pass
    elif update.message:
        reply_to = update.message.message_id
        await update.message.reply_text(contenido, parse_mode='Markdown', reply_to_message_id=reply_to)
        if tipo_media and tipo_media != 'texto' and media_id:
            try:
                if tipo_media == 'documento':
                    await context.bot.send_document(chat_id, media_id)
                elif tipo_media == 'foto':
                    await context.bot.send_photo(chat_id, media_id)
                elif tipo_media == 'video':
                    await context.bot.send_video(chat_id, media_id)
                elif tipo_media == 'audio':
                    await context.bot.send_audio(chat_id, media_id)
                elif tipo_media == 'voz':
                    await context.bot.send_voice(chat_id, media_id)
            except Exception:
                pass

async def limpiar_anuncios_profesor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite al profesor seleccionar un grupo y vaciar la base de datos de sus anuncios"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await query.edit_message_text("❌ Solo el profesor puede realizar esta acción.")
        return

    grupos = db.obtener_grupos_profesor(user.id)
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return

    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"🗑️ Borrar anuncios de {nombre}", callback_data=f"confirmar_borrar_anuncios_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    
    await query.edit_message_text(
        "🗑️ *BORRAR HISTORIAL DE ANUNCIOS*\n\n"
        "Selecciona el grupo del cual deseas eliminar todos los anuncios almacenados en la base de datos:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ejecutar_borrar_anuncios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta el borrado del historial de anuncios para el grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("confirmar_borrar_anuncios_", ""))
    user_id = query.from_user.id
    db = context.bot_data['db']

    if not await verificar_pertenencia_grupo(chat_id, user_id, db, query):
        return

    db.eliminar_anuncios_grupo(chat_id)
    await query.edit_message_text("✅ *Se han eliminado todos los anuncios de la base de datos para este grupo.*", parse_mode='Markdown')
