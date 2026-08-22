from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.ai_service import AIService
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = AIService()

async def compartir_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para compartir material de estudio"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_material'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 *COMPARTIR MATERIAL DE ESTUDIO*\n\n"
        "Envíame el material que deseas compartir con tus estudiantes.\n\n"
        "Puede ser:\n"
        "• Documento PDF / Word / PowerPoint\n"
        "• Imagen o Foto\n"
        "• Video de estudio\n"
        "• Link de página web o YouTube\n"
        "• Texto o referencia bibliográfica",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el material del profesor"""
    if not context.user_data.get('esperando_material'):
        return
    
    if not update.message:
        return
    
    material = None
    tipo_material = None
    descripcion = None
    
    if update.message.document:
        material = update.message.document
        tipo_material = 'documento'
        descripcion = update.message.caption or material.file_name
    elif update.message.photo:
        material = update.message.photo[-1]
        tipo_material = 'foto'
        descripcion = update.message.caption or "Imagen de estudio"
    elif update.message.video:
        material = update.message.video
        tipo_material = 'video'
        descripcion = update.message.caption or "Video de estudio"
    elif update.message.text:
        texto = update.message.text
        if texto.startswith('http://') or texto.startswith('https://'):
            material = texto
            tipo_material = 'link'
            descripcion = texto
        else:
            material = texto
            tipo_material = 'texto'
            descripcion = texto
    
    if not material:
        await update.message.reply_text(
            "❌ No se detectó ningún material. Por favor, envía un archivo, link o texto."
        )
        return
    
    context.user_data['material'] = material
    context.user_data['tipo_material'] = tipo_material
    context.user_data['esperando_material'] = False
    
    await update.message.reply_text("✨ Preparando material...")
    
    try:
        mensaje_intro = gemini.generar_mensaje_introductorio(descripcion)
        context.user_data['mensaje_intro'] = mensaje_intro
    except Exception:
        mensaje_intro = "Material de estudio compartido por el profesor."
        context.user_data['mensaje_intro'] = mensaje_intro
    
    await update.message.reply_text(
        f"✅ *Material recibido correctamente*\n\n"
        f"📝 Mensaje introductorio:\n"
        f"\"{mensaje_intro}\"\n\n"
        "¿Deseas enviarlo a un grupo?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Sí, enviar", callback_data="confirmar_material"),
                InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
            ]
        ])
    )

async def confirmar_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma y pregunta a qué grupo enviar"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    if not context.user_data.get('material'):
        await query.edit_message_text("❌ No hay material para enviar.")
        return
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"enviar_material_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 ¿A qué grupo deseas enviar el material?",
        reply_markup=reply_markup
    )

async def enviar_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el material al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("enviar_material_", ""))
    material = context.user_data.get('material')
    tipo = context.user_data.get('tipo_material')
    mensaje_intro = context.user_data.get('mensaje_intro', 'Material de estudio compartido por el profesor.')
    db = context.bot_data['db']

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return
    
    if not material:
        await query.edit_message_text("❌ No hay material para enviar.")
        return
    
    try:
        mensaje_completo = f"📚 *MATERIAL DE ESTUDIO*\n\n{mensaje_intro}"
        msg_enviado = None
        
        if tipo == 'documento':
            msg_enviado = await context.bot.send_document(chat_id, material, caption=mensaje_completo, parse_mode='Markdown')
        elif tipo == 'foto':
            msg_enviado = await context.bot.send_photo(chat_id, material, caption=mensaje_completo, parse_mode='Markdown')
        elif tipo == 'video':
            msg_enviado = await context.bot.send_video(chat_id, material, caption=mensaje_completo, parse_mode='Markdown')
        elif tipo == 'link':
            msg_enviado = await context.bot.send_message(chat_id, f"{mensaje_completo}\n\n🔗 {material}", parse_mode='Markdown')
        elif tipo == 'texto':
            msg_enviado = await context.bot.send_message(chat_id, mensaje_completo, parse_mode='Markdown')
        
        if msg_enviado:
            try:
                await context.bot.pin_chat_message(chat_id, msg_enviado.message_id)
            except Exception:
                pass

        await query.edit_message_text("✅ Material enviado y fijado exitosamente.")
        
        context.user_data.pop('material', None)
        context.user_data.pop('tipo_material', None)
        context.user_data.pop('mensaje_intro', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar el material: {str(e)}")
