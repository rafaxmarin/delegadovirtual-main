from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from gemini_handler import GeminiHandler
from docx import Document # type: ignore
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # type: ignore
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT # type: ignore
import os
import tempfile

async def redactar_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para redactar una minuta"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['esperando_minuta'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 *REDACCIÓN DE MINUTA*\n\n"
        "Envíame una nota de voz con la información de la ponencia, "
        "exposición o contenido que deseas estructurar.\n\n"
        "Yo lo redactaré siguiendo las normas APA 7ma edición.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def recibir_contenido_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el contenido para la minuta"""
    if not context.user_data.get('esperando_minuta') and not context.user_data.get('esperando_contenido_minuta'):
        return
    
    contenido = None
    
    # Verificar si es nota de voz
    if update.message.voice:
        await update.message.reply_text("🎙️ Procesando nota de voz...")
        # Simulación de transcripción (en producción usar Speech-to-Text)
        await update.message.reply_text(
            "✅ Nota de voz recibida. Por favor, confirma el contenido "
            "enviando un mensaje de texto con el resumen."
        )
        context.user_data['esperando_contenido_minuta'] = True
        return
    
    # Si es texto
    if update.message.text:
        contenido = update.message.text
    
    if context.user_data.get('esperando_contenido_minuta'):
        contenido = update.message.text
        context.user_data['esperando_contenido_minuta'] = False
    
    if not contenido:
        return
    
    # Guardar contenido
    context.user_data['contenido_minuta'] = contenido
    context.user_data['esperando_minuta'] = False
    
    # Preguntar formato
    keyboard = [
        [
            InlineKeyboardButton("📕 PDF", callback_data="formato_pdf"),
            InlineKeyboardButton("📘 Word", callback_data="formato_word")
        ],
        [
            InlineKeyboardButton("📙 Diapositiva", callback_data="formato_ppt"),
            InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📄 ¿En qué formato deseas la minuta?",
        reply_markup=reply_markup
    )

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
        # Generar contenido estructurado con Gemini
        if formato == "ppt":
            texto_apa = GeminiHandler.generar_minuta_apa(contenido, "diapositiva")
        else:
            texto_apa = GeminiHandler.generar_minuta_apa(contenido, "documento")
        
        # Generar archivo según formato
        if formato == "pdf":
            archivo = generar_pdf_apa(texto_apa)
        elif formato == "word":
            archivo = generar_word_apa(texto_apa)
        else:
            archivo = generar_pdf_apa(texto_apa)  # PPT como PDF por ahora
        
        # Guardar archivo en contexto
        context.user_data['archivo_minuta'] = archivo
        context.user_data['formato_minuta'] = formato
        
        # Mostrar vista previa
        with open(archivo, 'rb') as f:
            await context.bot.send_document(
                user.id,
                f,
                caption=(
                    "📄 *VISTA PREVIA DE LA MINUTA*\n\n"
                    "¿Deseas enviar este documento?\n"
                    "Selecciona una opción:"
                ),
                parse_mode='Markdown'
            )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Enviar a grupo", callback_data="enviar_minuta_grupo"),
                InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            user.id,
            "¿Qué deseas hacer con la minuta?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await context.bot.send_message(
            user.id,
            f"❌ Error al generar la minuta: {str(e)}"
        )

def generar_pdf_apa(contenido):
    """Genera un PDF con formato APA 7ma edición"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    doc = SimpleDocTemplate(
        temp_file.name,
        pagesize=letter,
        rightMargin=72,  # 1 pulgada
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo APA personalizado
    estilo_apa = ParagraphStyle(
        'APA',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=24,  # Doble espacio
        alignment=TA_JUSTIFY,
        firstLineIndent=36  # Sangría primera línea
    )
    
    estilo_titulo = ParagraphStyle(
        'TituloAPA',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        alignment=TA_CENTER,
        leading=24
    )
    
    # Construir contenido
    elementos = []
    
    # Procesar líneas
    lineas = contenido.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if linea:
            # Detectar títulos (mayúsculas o líneas cortas)
            if linea.isupper() or len(linea) < 60:
                elementos.append(Paragraph(linea, estilo_titulo))
            else:
                elementos.append(Paragraph(linea, estilo_apa))
            elementos.append(Spacer(1, 12))
    
    doc.build(elementos)
    return temp_file.name

def generar_word_apa(contenido):
    """Genera un documento Word con formato APA 7ma edición"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
    
    doc = Document()
    
    # Configurar márgenes (1 pulgada)
    for section in doc.sections:
        section.top_margin = 914400  # 1 pulgada en EMU
        section.bottom_margin = 914400
        section.left_margin = 914400
        section.right_margin = 914400
    
    # Estilo APA
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = 152400  # 12pt en EMU
    style.paragraph_format.line_spacing = 2.0
    style.paragraph_format.first_line_indent = 914400  # 0.5 pulgada
    
    # Agregar contenido
    lineas = contenido.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if linea:
            paragraph = doc.add_paragraph(linea)
            # Títulos centrados y en negrita
            if linea.isupper() or len(linea) < 60:
                paragraph.alignment = 1  # Centro
                paragraph.runs[0].bold = True
    
    doc.save(temp_file.name)
    return temp_file.name

async def enviar_minuta_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía la minuta al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    archivo = context.user_data.get('archivo_minuta')
    
    if not archivo:
        await query.edit_message_text("❌ No hay minuta para enviar.")
        return
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"despachar_minuta_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 ¿A qué grupo deseas enviar la minuta?",
        reply_markup=reply_markup
    )

async def despachar_minuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Despacha la minuta al grupo"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("despachar_minuta_", ""))
    archivo = context.user_data.get('archivo_minuta')
    formato = context.user_data.get('formato_minuta', 'documento')
    
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
        
        # Limpiar archivo temporal
        try:
            os.unlink(archivo)
        except:
            pass
        
        context.user_data.pop('archivo_minuta', None)
        context.user_data.pop('contenido_minuta', None)
        context.user_data.pop('formato_minuta', None)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error al enviar la minuta: {str(e)}")
