import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.infrastructure.documents.pdf_exporter import generar_pdf_apa
from src.infrastructure.documents.docx_exporter import generar_word_apa

gemini = GeminiAdapter()

async def redactar_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para redactar una minuta"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_minuta'] = True
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    
    await query.edit_message_text(
        "📝 *REDACCIÓN DE MINUTA*\n\n"
        "Envíame la información o resumen de la ponencia para estructurar la minuta APA 7ma edición.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def recibir_contenido_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el contenido para la minuta"""
    if not context.user_data.get('esperando_minuta'):
        return
    
    contenido = update.message.text
    if not contenido:
        return
    
    context.user_data['contenido_minuta'] = contenido
    context.user_data['esperando_minuta'] = False
    
    keyboard = [
        [
            InlineKeyboardButton("📕 PDF", callback_data="formato_pdf"),
            InlineKeyboardButton("📘 Word", callback_data="formato_word")
        ],
        [InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]
    ]
    await update.message.reply_text("📄 ¿En qué formato deseas la minuta?", reply_markup=InlineKeyboardMarkup(keyboard))

async def generar_minuta_formato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera la minuta en el formato seleccionado"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    formato = query.data.replace("formato_", "")
    contenido = context.user_data.get('contenido_minuta')
    
    if not contenido:
        await query.edit_message_text("❌ No hay contenido para generar la minuta.")
        return
    
    await query.edit_message_text("⏳ Generando documento con normas APA 7ma edición...")
    
    try:
        texto_apa = gemini.generar_minuta_apa(contenido, "documento")
        
        if formato == "pdf":
            archivo = generar_pdf_apa(texto_apa)
        elif formato == "word":
            archivo = generar_word_apa(texto_apa)
        else:
            archivo = generar_pdf_apa(texto_apa)
        
        context.user_data['archivo_minuta'] = archivo
        context.user_data['formato_minuta'] = formato
        
        with open(archivo, 'rb') as f:
            await context.bot.send_document(
                user.id,
                f,
                caption="📄 *VISTA PREVIA DE LA MINUTA*\n\n¿Deseas enviar este documento?",
                parse_mode='Markdown'
            )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Enviar a grupo", callback_data="enviar_minuta_grupo"),
                InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
            ]
        ]
        await context.bot.send_message(user.id, "¿Qué deseas hacer con la minuta?", reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        await context.bot.send_message(user.id, f"❌ Error al generar la minuta: {str(e)}")

async def enviar_minuta_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra grupos para enviar la minuta"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(query.from_user.id)
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = [[InlineKeyboardButton(f"📚 {nombre}", callback_data=f"despachar_minuta_{chat_id}")] for chat_id, nombre in grupos]
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    
    await query.edit_message_text("📋 ¿A qué grupo deseas enviar la minuta?", reply_markup=InlineKeyboardMarkup(keyboard))

async def despachar_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía la minuta al grupo"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("despachar_minuta_", ""))
    archivo = context.user_data.get('archivo_minuta')
    
    if not archivo:
        await query.edit_message_text("❌ No hay minuta para enviar.")
        return
    
    try:
        with open(archivo, 'rb') as f:
            await context.bot.send_document(
                chat_id,
                f,
                caption="📝 *MINUTA ACADÉMICA*\n\nDocumento elaborado siguiendo normas APA 7ma edición.",
                parse_mode='Markdown'
            )
        await query.edit_message_text("✅ Minuta enviada exitosamente al grupo.")
        try: os.unlink(archivo)
        except: pass
        context.user_data.pop('archivo_minuta', None)
        context.user_data.pop('contenido_minuta', None)
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar la minuta: {str(e)}")
