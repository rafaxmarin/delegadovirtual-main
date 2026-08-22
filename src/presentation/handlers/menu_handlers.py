from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.presentation.keyboards import get_menu_keyboard, get_estudiante_menu_keyboard
from src.presentation.handlers.recaudacion_handlers import obtener_codigo_banco, limpiar_cedula, limpiar_telefono

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /menu y despliega el menú (Profesor o Estudiante Verificado)"""
    user = update.effective_user
    db = context.bot_data['db']
    
    es_profesor = db.es_profesor_verificado(user.id)
    es_estudiante = db.es_estudiante_verificado(user.id)
    
    if es_profesor:
        texto_menu = (
            "📋 *MENÚ PRINCIPAL DE PROFESOR*\n\n"
            "Selecciona la función que deseas utilizar:"
        )
        reply_markup = get_menu_keyboard()
    elif es_estudiante:
        texto_menu = (
            "🎓 *MENÚ DE ESTUDIANTES — Delegado Virtual*\n\n"
            "¡Hola! Selecciona una opción o utiliza los siguientes comandos en tu grupo:\n\n"
            "💸 *Recaudaciones y Pagos:*\n"
            "• `/recaudacion` — Consulta los datos de la recaudación activa del grupo.\n"
            "• `/pago` — Valida tu captura de comprobante de pago en el grupo.\n"
            "• `/efectivo` — Registra un pago en efectivo al profesor en el grupo.\n\n"
            "❓ *Asesorías y Preguntas:*\n"
            "• `/pregunta [tu duda]` — Envía una duda directamente al buzón del profesor."
        )
        reply_markup = get_estudiante_menu_keyboard()
    else:
        texto_menu = (
            "⚠️ *ACCESO RESTRINGIDO*\n\n"
            "El comando `/menu` está reservado exclusivamente para **profesores** y **estudiantes verificados**.\n\n"
            "🎓 *Si eres estudiante:* Para verificar tu cuenta y acceder al bot, ingresa al grupo de tu materia mediante el enlace de invitación de tu profesor o presiona el botón *🔐 Verificar Cédula en privado* en tu grupo."
        )
        keyboard = [[InlineKeyboardButton("❌ Cerrar panel", callback_data="menu_cerrar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                texto_menu,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception:
            await update.callback_query.message.reply_text(
                texto_menu,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    elif update.message:
        await update.message.reply_text(
            texto_menu,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde un callback button y limpia el estado activo"""
    await menu(update, context)

async def cerrar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cierra/elimina el mensaje del menú al hacer clic en Cerrar"""
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.delete_message()
        except Exception:
            await query.edit_message_text("✅ Panel cerrado.")

async def estudiante_recaudacion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Consultar Recaudación del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()
    
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    db = context.bot_data['db']

    if chat_type == 'private':
        texto = (
            "📌 *Consulta de Recaudación en Grupo*\n\n"
            "Para consultar los datos de pago activo, debes usar el botón o el comando `/recaudacion` **dentro del grupo de tu materia** donde está registrado el bot."
        )
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        await query.edit_message_text(texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
        texto = "⚠️ *No hay ninguna recaudación activa en este grupo en este momento.*"
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    else:
        rec_id, profesor_id, g_id, concepto, monto, banco, cedula, telefono, fecha_limite, activa = rec_tuple[:10]
        monto = float(monto)
        pagos = db.obtener_pagos_recaudacion(rec_id)
        total_pagados = len(pagos)

        cod_banco = obtener_codigo_banco(str(banco))
        ced_clean = limpiar_cedula(str(cedula))
        tel_clean = limpiar_telefono(str(telefono))
        monto_clean = f"{monto:.2f}"

        texto = (
            f"💸 *RECAUDACIÓN ACTIVA DEL GRUPO*\n\n"
            f"📝 *Concepto:* {concepto}\n"
            f"💵 *Monto requerimiento:* Bs. {monto:,.2f}\n\n"
            f"💳 *DATOS PARA PAGO MÓVIL (DESTINO):*\n"
            f"1️⃣ *Código de Banco ({banco}):*\n`{cod_banco}`\n"
            f"2️⃣ *Cédula / RIF:*\n`{ced_clean}`\n"
            f"3️⃣ *Teléfono:*\n`{tel_clean}`\n"
            f"4️⃣ *Monto:*\n`{monto_clean}`\n\n"
            f"⏰ *Fecha Límite:* {fecha_limite}\n"
            f"👥 *Pagos validados:* {total_pagados}"
        )
        keyboard = [
            [InlineKeyboardButton("📋 Copiar Datos de Pago", callback_data=f"copiar_datos_pago_{rec_id}")],
            [InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]
        ]
    await query.edit_message_text(texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_pago_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Guía para subir Pago del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "📷 *GUÍA PARA REGISTRAR TU PAGO*\n\n"
        "1. Entra al grupo de tu clase donde está el bot.\n"
        "2. *Si pagaste por Pago Móvil:* Envía la captura/imagen del comprobante (o usa `/pago`).\n"
        "3. *Si pagaste en efectivo al profesor:* Ejecuta el comando `/efectivo` en el grupo.\n"
        "4. El bot registrará tu pago en la lista en vivo en tiempo real."
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    await query.edit_message_text(guia, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_pregunta_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Guía para hacer una Pregunta al Profesor"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "❓ *GUÍA PARA HACER PREGUNTAS AL PROFESOR*\n\n"
        "Para realizar una consulta académica sin saturar el grupo:\n\n"
        "• Escribe el comando `/pregunta` seguido de tu duda.\n"
        "• *Ejemplo:* `/pregunta Profe, ¿cuál es el tema que entra en la evaluación de mañana?`\n\n"
        "La pregunta llegará directamente al buzón privado del profesor para ser respondida."
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    await query.edit_message_text(guia, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_anuncios_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Anuncios del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "📢 *ANUNCIOS OFICIALES DEL PROFESOR*\n\n"
        "Los comunicados oficiales, notas de voz estructuradas y avisos del profesor se publican directamente en el chat del grupo.\n\n"
        "📌 *Todos los anuncios son FIJADOS automáticamente en la parte superior del grupo.* Puedes presionar el mensaje fijado en Telegram para consultar el último anuncio rápidamente."
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    await query.edit_message_text(guia, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_material_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Materiales del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "📚 *MATERIAL DE ESTUDIO*\n\n"
        "El profesor comparte guías, PDFs, documentos Word, enlaces y videos de estudio en el grupo de la materia.\n\n"
        "📌 *Todo el material compartido queda FIJADO en el grupo* para que puedas acceder a él en cualquier momento desde los mensajes anclados del chat."
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    await query.edit_message_text(guia, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_reglamento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Reglamento del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "📜 *REGLAMENTO Y NORMAS DEL GRUPO*\n\n"
        "El profesor establece las normas de convivencia y evaluación de la materia.\n\n"
        "📌 *El reglamento oficial permanece FIJADO en la parte superior del grupo.* Te invitamos a leerlo para mantener el respeto y cumplir los lineamientos del curso."
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    await query.edit_message_text(guia, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
