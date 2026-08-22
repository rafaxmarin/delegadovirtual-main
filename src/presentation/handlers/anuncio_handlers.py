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
        
        await query.edit_message_text("✅ Anuncio enviado exitosamente.")
        context.user_data.pop('anuncio_formal', None)
        context.user_data.pop('anuncio_media', None)
        context.user_data.pop('tipo_anuncio_media', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar el anuncio: {str(e)}")
