from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.presentation.keyboards import get_menu_keyboard, get_estudiante_menu_keyboard
from src.presentation.handlers.recaudacion_handlers import obtener_codigo_banco, limpiar_cedula, limpiar_telefono

async def es_estudiante_verificado_y_en_grupo(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica que el usuario sea un estudiante verificado Y pertenezca activamente a al menos un grupo registrado"""
    db = context.bot_data['db']
    
    if not db.es_estudiante_verificado(user_id):
        return False
        
    grupos = db.obtener_todos_los_grupos()
    for chat_id, _ in grupos:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except Exception:
            continue
            
    return False

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /menu y despliega el menú (Profesor o Estudiante Verificado e Integrado en Grupo)"""
    user = update.effective_user
    db = context.bot_data['db']
    
    es_profesor = db.es_profesor_verificado(user.id)
    es_estudiante_valido = await es_estudiante_verificado_y_en_grupo(user.id, context)
    
    if es_profesor:
        texto_menu = (
            "📋 *MENÚ PRINCIPAL DE PROFESOR*\n\n"
            "Selecciona la función que deseas utilizar:"
        )
        reply_markup = get_menu_keyboard()
    elif es_estudiante_valido:
        texto_menu = (
            "🎓 *MENÚ DE ESTUDIANTES — Delegado Virtual*\n\n"
            "¡Hola! Selecciona una opción o utiliza los siguientes comandos en tu grupo:\n\n"
            "💸 *Recaudaciones y Pagos:*\n"
            "• `/recaudacion` — Consulta los datos de la recaudación activa del grupo.\n"
            "• `/pago <referencia> [nombres]` — Reporta tu pago móvil en el grupo.\n"
            "• `/efectivo` — Registra un pago en efectivo al profesor en el grupo.\n\n"
            "❓ *Asesorías y Preguntas:*\n"
            "• `/pregunta [tu duda]` — Envía una duda directamente al buzón del profesor."
        )
        reply_markup = get_estudiante_menu_keyboard()
    else:
        texto_menu = (
            "⚠️ *ACCESO RESTRINGIDO*\n\n"
            "El comando `/menu` está reservado exclusivamente para **profesores** y **estudiantes verificados activos dentro del grupo**.\n\n"
            "🎓 *Si eres estudiante:* Para acceder al bot debes ingresar al grupo de tu materia y asegurarte de que tu solicitud haya sido APROBADA con tu nombre y apellido de Telegram verificados."
        )
        keyboard = [[InlineKeyboardButton("❌ Cerrar panel", callback_data="menu_cerrar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(texto_menu, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(texto_menu, reply_markup=reply_markup, parse_mode='Markdown')

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retorna al menú principal para estudiantes o profesores según su rol"""
    query = update.callback_query
    if query:
        await query.answer()
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
    """Acción del botón Recaudación del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    db = context.bot_data['db']
    user_id = query.from_user.id
    
    # Obtener el chat del grupo al que pertenece el estudiante
    chat_id = None
    if update.effective_chat and update.effective_chat.type != 'private':
        chat_id = update.effective_chat.id
    else:
        # Buscar en pendientes de verificación resueltos para identificar su grupo
        db.cursor.execute('SELECT chat_id FROM pendientes_verificacion WHERE user_id = ? AND resuelto = 1 ORDER BY id DESC LIMIT 1', (user_id,))
        row = db.cursor.fetchone()
        target_chat_id = row[0] if row else None
        
        # Si no lo encontramos por pendientes, buscar por miembros_telegram
        if not target_chat_id:
            db.cursor.execute('SELECT chat_id FROM miembros_telegram WHERE user_id = ? ORDER BY fecha_visto DESC LIMIT 1', (user_id,))
            row_m = db.cursor.fetchone()
            target_chat_id = row_m[0] if row_m else None

        if not target_chat_id:
            texto = "⚠️ *No se pudo identificar tu grupo de materia.* Asegúrate de estar dentro del grupo de Telegram."
            keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
            await query.edit_message_text(texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        chat_id = target_chat_id

    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
        texto = "⚠️ *No hay ninguna recaudación activa en tu grupo en este momento.*"
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
            f"👥 *Pagos registrados:* {total_pagados}\n\n"
            f"📌 *INSTRUCCIONES DE REGISTRO DE PAGO:*\n"
            f"• 📲 *Pago Móvil:* Escribe en el grupo `/pago <referencia> [nombres]`.\n"
            f"  _Ejemplo múltiple:_ `/pago 564654654646564 Alan Brito y Solomeo Paredes`\n"
            f"  _Ejemplo individual:_ `/pago 564654654646564`\n"
            f"• 💵 *Efectivo:* Ejecuta `/efectivo` en el grupo si pagaste en físico al profesor."
        )
        keyboard = [
            [InlineKeyboardButton("📋 Copiar Datos de Pago", callback_data=f"copiar_datos_pago_{rec_id}")],
            [InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]
        ]
    await query.edit_message_text(texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def estudiante_guia_pago_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción del botón Guía para reportar Pago del menú de estudiante"""
    query = update.callback_query
    if query:
        await query.answer()

    guia = (
        "💳 *GUÍA PARA REPORTAR TU PAGO*\n\n"
        "Para registrar tu pago móvil en el grupo de tu materia, usa el comando `/pago` indicando el número de referencia y el/los nombres de los estudiantes:\n\n"
        "📌 *Ejemplos de uso en el grupo:*\n"
        "• *Si pagas solo por ti:*\n"
        "  `/pago 564654654646564`\n"
        "  o `/pago 564654654646564 Tu Nombre y Apellido`\n\n"
        "• *Si pagas por varios estudiantes:*\n"
        "  `/pago 564654654646564 Alan Brito y Solomeo Paredes`\n\n"
        "💵 *Pago en Efectivo:* Si le pagaste en físico al profesor, ejecuta `/efectivo` en el grupo.\n\n"
        "✅ El bot registrará el pago y guardará la referencia para la comprobación del profesor."
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
    """Acción del botón Anuncios del menú de estudiante (despliega el último anuncio registrado)"""
    from src.presentation.handlers.anuncio_handlers import consultar_ultimo_anuncio
    await consultar_ultimo_anuncio(update, context)

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
