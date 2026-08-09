from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json, re
from datetime import datetime
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = GeminiAdapter()

async def menu_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el submenú de Recaudación (Crear nueva o Ver reporte)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ Crear nueva recaudación", callback_data="iniciar_crear_recaudacion")],
        [InlineKeyboardButton("📊 Ver reporte de pagos", callback_data="ver_reporte_recaudacion_menu")],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "💰 *GESTIÓN DE RECAUDACIONES*\n\n"
        "Selecciona la opción deseada:\n\n"
        "• ➕ *Crear nueva recaudación:* Inicia el registro de una nueva recaudación para un grupo. (Los datos de la recaudación anterior de ese grupo se borrarán).\n"
        "• 📊 *Ver reporte de pagos:* Muestra el informe en vivo y detalle de pagos recibidos por grupo."
    )

    if query:
        await query.edit_message_text(texto, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(texto, parse_mode='Markdown', reply_markup=reply_markup)

async def iniciar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de creación de recaudación"""
    query = update.callback_query
    if query:
        await query.answer()
    
    context.user_data['creando_recaudacion'] = True
    context.user_data['recaudacion_datos'] = {}
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="menu_recaudacion")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_texto = (
        "💰 *CREAR NUEVA RECAUDACIÓN*\n\n"
        "Dime los datos de la recaudación. Puedes escribirlo en un solo mensaje "
        "o por partes. Necesito:\n"
        "• 📝 Concepto\n• 💵 Monto (Bs.)\n• 🏦 Banco\n• 🪪 Cédula\n• 📱 Teléfono\n• ⏰ Fecha límite\n\n"
        "Ejemplo: \"Exámenes Unidad I, 120, Mercantil, 12345678, 04121234567, 15/07/2026 23:59\"\n\n"
        "💡 *Nota:* Al confirmar y enviar la recaudación a un grupo, se borrarán automáticamente los datos de la recaudación anterior de ese grupo."
    )

    if query:
        await query.edit_message_text(msg_texto, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(msg_texto, parse_mode='Markdown', reply_markup=reply_markup)

async def procesar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa los datos de recaudación con IA de manera flexible"""
    if not context.user_data.get('creando_recaudacion'):
        return
    
    mensaje = update.message.text
    if not mensaje:
        return
    
    if mensaje.lower() in ['cancelar', 'cancel', 'salir', 'no']:
        context.user_data.pop('creando_recaudacion', None)
        context.user_data.pop('recaudacion_datos', None)
        await update.message.reply_text("✅ Recaudación cancelada. Usa /menu para volver.")
        return
    
    msg_procesando = await update.message.reply_text("🔍 *Analizando tu mensaje...*", parse_mode='Markdown')
    
    try:
        datos_actuales = context.user_data.get('recaudacion_datos', {})
        prompt = f"""
        Analiza el siguiente mensaje y extrae información de recaudación.
        Mensaje del profesor: "{mensaje}"
        Datos que ya tenemos: {json.dumps(datos_actuales, ensure_ascii=False)}
        Identifica: concepto, monto, banco, cedula, telefono, fecha_limite.
        Responde EXCLUSIVAMENTE en JSON:
        {{"concepto": "...", "monto": 0, "banco": "...", "cedula": "...", "telefono": "...", "fecha_limite": "..."}}
        Si un campo no aparece, usa "no_encontrado".
        """
        resultado = gemini.model.generate_content(prompt).text.strip()
        resultado = resultado.replace('```json', '').replace('```', '').strip()
        
        try:
            datos_nuevos = json.loads(resultado)
        except Exception:
            json_match = re.search(r'\{.*\}', resultado, re.DOTALL)
            if json_match:
                datos_nuevos = json.loads(json_match.group())
            else:
                raise Exception("No se pudo interpretar la respuesta JSON")
        
        for clave, valor in datos_nuevos.items():
            if valor and valor != "no_encontrado" and valor != 0:
                datos_actuales[clave] = valor
        
        context.user_data['recaudacion_datos'] = datos_actuales
        
        campos = ['concepto', 'monto', 'banco', 'cedula', 'telefono', 'fecha_limite']
        completos = [c for c in campos if datos_actuales.get(c) and datos_actuales.get(c) not in ["no_encontrado", 0]]
        faltantes = [c for c in campos if c not in completos]
        
        await msg_procesando.delete()
        
        if faltantes:
            mensaje_progreso = "📊 *PROGRESO DE RECAUDACIÓN*\n\n"
            for c in campos:
                if c in completos:
                    mensaje_progreso += f"✅ {c.capitalize()}: {datos_actuales.get(c)}\n"
                else:
                    mensaje_progreso += f"⬜ {c.capitalize()}: *PENDIENTE*\n"
            mensaje_progreso += "\n✏️ Puedes enviarme los datos faltantes en otro mensaje."
            await update.message.reply_text(mensaje_progreso, parse_mode='Markdown')
        else:
            context.user_data['creando_recaudacion'] = False
            monto = float(str(datos_actuales['monto']).replace(',', '.'))
            
            resumen = (
                f"✅ *¡RECAUDACIÓN LISTA PARA INICIAR!*\n\n"
                f"📝 *Concepto:* {datos_actuales['concepto']}\n"
                f"💵 *Monto:* Bs. {monto:,.2f}\n"
                f"🏦 *Banco Destino:* {datos_actuales['banco']}\n"
                f"🪪 *Cédula:* {datos_actuales['cedula']}\n"
                f"📱 *Teléfono:* {datos_actuales['telefono']}\n"
                f"⏰ *Fecha Límite:* {datos_actuales['fecha_limite']}\n\n"
                "¿Deseas enviar esta recaudación al grupo? (Si existía una previa en ese grupo, se eliminarán sus datos)"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ Enviar a grupo", callback_data="confirmar_recaudacion"),
                    InlineKeyboardButton("🔄 Corregir", callback_data="iniciar_crear_recaudacion")
                ],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_recaudacion")]
            ]
            await update.message.reply_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        try: await msg_procesando.delete()
        except: pass
        await update.message.reply_text(f"⚠️ Error al procesar los datos: {str(e)}")

async def confirmar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra grupos para enviar recaudación"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(query.from_user.id)
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = [[InlineKeyboardButton(f"📚 {nombre}", callback_data=f"enviar_recaudacion_{chat_id}")] for chat_id, nombre in grupos]
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="menu_recaudacion")])
    
    await query.edit_message_text("📋 ¿A qué grupo deseas enviar esta recaudación?", reply_markup=InlineKeyboardMarkup(keyboard))

async def enviar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía la recaudación al grupo, inicia la lista en vivo y borra datos anteriores del grupo"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    chat_id = int(query.data.replace("enviar_recaudacion_", ""))
    datos = context.user_data.get('recaudacion_datos', {})

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return

    monto = float(str(datos['monto']).replace(',', '.'))
    
    # Crear nueva recaudación (esto desactiva la previa y limpia pagos anteriores del grupo)
    rec_id = db.crear_recaudacion(
        query.from_user.id, chat_id, str(datos['concepto']), monto,
        str(datos['banco']), str(datos['cedula']), str(datos['telefono']), str(datos['fecha_limite'])
    )
    
    mensaje_anuncio = (
        f"💸 *NUEVA RECAUDACIÓN AUTORIZADA*\n\n"
        f"📝 *Concepto:* {datos['concepto']}\n"
        f"💵 *Monto requerimiento:* Bs. {monto:,.2f}\n\n"
        f"💳 *DATOS DE PAGO MÓVIL (DESTINO):*\n"
        f"🏦 *Banco:* {datos['banco']}\n"
        f"🪪 *Cédula:* {datos['cedula']}\n"
        f"📱 *Teléfono:* {datos['telefono']}\n\n"
        f"⏰ *Fecha Límite:* {datos['fecha_limite']}\n\n"
        f"📷 *INSTRUCCIONES DE VERIFICACIÓN (IA):*\n"
        f"Para registrar tu pago, envía la captura del comprobante a este grupo.\n"
        f"La imagen debe mostrar claramente:\n"
        f"• Fecha y hora de la transacción\n"
        f"• Tu nombre o titular origen\n"
        f"• Número de referencia / transacción\n"
        f"• Banco destino (*DEBE ser {datos['banco']}*)\n"
        f"• Monto correcto (Bs. {monto:,.2f})"
    )
    
    msg_anuncio = await context.bot.send_message(chat_id, mensaje_anuncio, parse_mode='Markdown')
    try: await context.bot.pin_chat_message(chat_id, msg_anuncio.message_id)
    except: pass

    # Mensaje de lista en vivo inicial
    mensaje_lista = (
        f"📊 *ESTADO DE PAGOS EN VIVO*\n"
        f"📝 *Concepto:* {datos['concepto']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Aún no hay pagos validados.*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Pagados:* 0\n"
        f"💵 *Total Recaudado:* Bs. 0.00\n"
        f"⏰ *Fecha Límite:* {datos['fecha_limite']}"
    )
    
    msg_lista = await context.bot.send_message(chat_id, mensaje_lista, parse_mode='Markdown')
    db.actualizar_mensaje_lista(rec_id, msg_lista.message_id)
    
    await query.edit_message_text("✅ Recaudación enviada exitosamente. Se ha iniciado la lista en vivo en el grupo.")

async def ver_reporte_recaudacion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de grupos del profesor para ver su reporte de recaudación"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(query.from_user.id)
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="menu_recaudacion")]]))
        return
    
    keyboard = [[InlineKeyboardButton(f"📚 {nombre}", callback_data=f"reporte_rec_grupo_{chat_id}")] for chat_id, nombre in grupos]
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú de recaudación", callback_data="menu_recaudacion")])
    
    await query.edit_message_text("📊 Selecciona el grupo para ver el reporte de recaudación:", reply_markup=InlineKeyboardMarkup(keyboard))

async def ver_reporte_recaudacion_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el reporte detallado de recaudación del grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']

    chat_id = int(query.data.replace("reporte_rec_grupo_", ""))

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return

    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    
    # Si no hay activa, buscar la última recaudación
    if not rec_tuple:
        db.cursor.execute('SELECT * FROM recaudaciones WHERE grupo_id = ? ORDER BY id DESC LIMIT 1', (chat_id,))
        rec_tuple = db.cursor.fetchone()

    if not rec_tuple:
        await query.edit_message_text(
            "❌ No hay recaudaciones registradas para este grupo.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="ver_reporte_recaudacion_menu")]])
        )
        return

    rec_id, profesor_id, g_id, concepto, monto_unitario, banco, cedula, telefono, fecha_limite, activa = rec_tuple[:10]
    monto_unitario = float(monto_unitario)
    estado_str = "🟢 Activa" if activa == 1 else "🔴 Finalizada"

    pagos = db.obtener_pagos_recaudacion(rec_id)
    cant_estudiantes = len(pagos)
    total_recaudado = cant_estudiantes * monto_unitario

    lineas_pagos = []
    if pagos:
        for p in pagos:
            ref = f"#{p[3]}" if len(p) > 3 and p[3] else ""
            lineas_pagos.append(f"• ✅ *{p[0]}* {ref} — {p[1]}")
        detalle_pagos_str = "\n".join(lineas_pagos)
    else:
        detalle_pagos_str = "⏳ *Ningún pago registrado aún.*"

    reporte_texto = (
        f"📋 *REPORTE DE RECAUDACIÓN*\n\n"
        f"📝 *Concepto:* {concepto}\n"
        f"📌 *Estado:* {estado_str}\n"
        f"💵 *Monto por estudiante:* Bs. {monto_unitario:,.2f}\n"
        f"🏦 *Banco Destino:* {banco}\n"
        f"💰 *Total Recaudado:* Bs. {total_recaudado:,.2f}\n"
        f"👥 *Estudiantes que pagaron:* {cant_estudiantes}\n"
        f"⏰ *Fecha límite:* {fecha_limite}\n\n"
        f"📜 *Detalle de comprobantes validados:*\n"
        f"{detalle_pagos_str}"
    )

    keyboard = [[InlineKeyboardButton("🔙 Volver a la lista de grupos", callback_data="ver_reporte_recaudacion_menu")]]
    await query.edit_message_text(reporte_texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def actualizar_lista_en_vivo(bot, chat_id: int, db, rec_id: int, concepto: str, monto_unitario: float, fecha_limite: str, mensaje_lista_id: int):
    """Actualiza en tiempo real el mensaje de lista en vivo en el grupo o envía uno nuevo si no existe"""
    pagos = db.obtener_pagos_recaudacion(rec_id)
    total_pagados = len(pagos)
    monto_total = total_pagados * monto_unitario

    if pagos:
        lineas = []
        for p in pagos:
            nombre = p[0]
            ref = f"#{p[3]}" if len(p) > 3 and p[3] else ""
            lineas.append(f"✅ *{nombre}* {ref}".strip())
        lista_str = "\n".join(lineas)
    else:
        lista_str = "⏳ *Aún no hay pagos validados.*"

    texto_actualizado = (
        f"📊 *ESTADO DE PAGOS EN VIVO*\n"
        f"📝 *Concepto:* {concepto}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{lista_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Pagados:* {total_pagados}\n"
        f"💵 *Total Recaudado:* Bs. {monto_total:,.2f}\n"
        f"⏰ *Fecha Límite:* {fecha_limite}"
    )

    actualizado = False
    if mensaje_lista_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=mensaje_lista_id,
                text=texto_actualizado,
                parse_mode='Markdown'
            )
            actualizado = True
        except Exception as e:
            print(f"⚠️ No se pudo editar mensaje anterior de lista en vivo: {e}")

    # Si no existía o falló editar el mensaje anterior, publicamos uno nuevo en el grupo
    if not actualizado:
        try:
            msg_nuevo = await bot.send_message(chat_id, texto_actualizado, parse_mode='Markdown')
            db.actualizar_mensaje_lista(rec_id, msg_nuevo.message_id)
        except Exception as e:
            print(f"⚠️ No se pudo publicar nuevo mensaje de lista en vivo: {e}")

async def validar_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida la captura enviada en el grupo (soporta fotos e imágenes enviadas directamente o con el comando /pago)"""
    if not update.message:
        return
    
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    user = update.effective_user
    estudiante_nombre = user.full_name or (f"@{user.username}" if user.username else "Estudiante")

    # Si se envía por chat privado
    if chat_type == 'private':
        await update.message.reply_text(
            "📌 *Por favor envía tu comprobante de pago directamente en el grupo de tu materia* donde está el bot para que sea validado y registrado en la lista pública.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
    elif update.message.document:
        doc = update.message.document
        mime = doc.mime_type or ""
        fname = doc.file_name or ""
        if mime.startswith('image/') or fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.heic')):
            photo_file_id = doc.file_id
    
    if not photo_file_id:
        if update.message.text and '/pago' in update.message.text:
            await update.message.reply_text(
                "📸 *Por favor adjunta la imagen/captura de tu comprobante de pago* al usar el comando `/pago`.",
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id
            )
        return

    print(f"📸 Imagen/Comprobante recibido de {estudiante_nombre} en chat ID: {chat_id}")

    db = context.bot_data['db']

    # Solo procesar si el grupo tiene una recaudación activa
    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
        print(f"⚠️ El chat {chat_id} no tiene una recaudación activa en la base de datos.")
        await update.message.reply_text(
            "⚠️ *No hay ninguna recaudación activa en este grupo en este momento.*\n\n"
            "El profesor aún no ha creado ni publicado un proceso de cobro activo para este grupo.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Extraer campos de recaudación
    rec_id = rec_tuple[0]
    profesor_id = rec_tuple[1]
    concepto = rec_tuple[3]
    monto_esperado = float(rec_tuple[4])
    banco_esperado = rec_tuple[5]
    cedula_esperada = rec_tuple[6]
    telefono_esperado = rec_tuple[7]
    fecha_limite = rec_tuple[8]
    mensaje_lista_id = rec_tuple[10] if len(rec_tuple) > 10 else None

    # Verificar si el estudiante ya registró un pago para esta recaudación
    if db.estudiante_ya_pago(rec_id, user.id, estudiante_nombre):
        await update.message.reply_text(
            f"⚠️ *{estudiante_nombre}*, ya tienes un pago verificado para la recaudación *{concepto}*.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    msg_procesando = await update.message.reply_text("🔍 *Analizando comprobante con visión IA...*", parse_mode='Markdown', reply_to_message_id=update.message.message_id)

    try:
        photo_file = await context.bot.get_file(photo_file_id)
        image_bytes = await photo_file.download_as_bytearray()

        datos_recaudacion = {
            "concepto": concepto,
            "monto": monto_esperado,
            "banco": banco_esperado,
            "cedula": cedula_esperada,
            "telefono": telefono_esperado,
            "fecha_limite": fecha_limite
        }

        evaluacion = gemini.validar_comprobante_contra_recaudacion(bytes(image_bytes), datos_recaudacion)
        await msg_procesando.delete()

        if evaluacion.get('valido'):
            num_ref = evaluacion.get('numero_verificacion', 'S/R')
            fecha_pago = evaluacion.get('fecha_pago') or datetime.now().strftime("%d/%m/%Y %H:%M")
            banco_det = evaluacion.get('banco_detectado', banco_esperado)

            # Registrar pago en DB
            db.registrar_pago(
                recaudacion_id=rec_id,
                estudiante_nombre=estudiante_nombre,
                fecha_pago=fecha_pago,
                estudiante_id=user.id,
                numero_verificacion=num_ref
            )

            # 1. NOTIFICAR EN EL GRUPO QUE EL PAGO ES VÁLIDO
            await update.message.reply_text(
                f"✅ *¡PAGO VÁLIDO Y VERIFICADO!*\n\n"
                f"👤 *Estudiante:* {estudiante_nombre}\n"
                f"🔢 *Ref / Comprobante:* #{num_ref}\n"
                f"🏦 *Banco Destino:* {banco_det}\n"
                f"💵 *Monto:* Bs. {monto_esperado:,.2f}\n"
                f"📅 *Fecha:* {fecha_pago}",
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id
            )

            # 2. ACTUALIZAR LISTA EN VIVO EN EL GRUPO
            await actualizar_lista_en_vivo(
                context.bot, chat_id, db, rec_id, concepto, monto_esperado, fecha_limite, mensaje_lista_id
            )

            # 3. NOTIFICAR AL PROFESOR EN PRIVADO
            total_pagos = db.contar_pagos(rec_id)
            total_recaudado = total_pagos * monto_esperado
            try:
                chat_info = await context.bot.get_chat(chat_id)
                nombre_grupo = chat_info.title
            except:
                nombre_grupo = "Grupo"

            notificacion_profesor = (
                f"💸 *NUEVO PAGO RECIBIDO Y VALIDADO*\n\n"
                f"📚 *Grupo:* {nombre_grupo}\n"
                f"📝 *Concepto:* {concepto}\n"
                f"👤 *Estudiante:* {estudiante_nombre}\n"
                f"🔢 *Verificación:* #{num_ref}\n"
                f"💵 *Monto:* Bs. {monto_esperado:,.2f}\n\n"
                f"📊 *Acumulado:* {total_pagos} pago(s) (Bs. {total_recaudado:,.2f})"
            )
            try:
                await context.bot.send_message(profesor_id, notificacion_profesor, parse_mode='Markdown')
            except Exception:
                pass

        else:
            motivo = evaluacion.get('motivo_rechazo', 'La captura no cumple con los requisitos esperados.')
            banco_det = evaluacion.get('banco_detectado', 'Desconocido')

            # 1. NOTIFICAR EN EL GRUPO QUE EL PAGO NO ES VÁLIDO
            await update.message.reply_text(
                f"❌ *PAGO NO VÁLIDO / RECHAZADO*\n\n"
                f"👤 *Estudiante:* {estudiante_nombre}\n"
                f"⚠️ *Motivo:* {motivo}\n"
                f"🏦 *Banco Detectado:* {banco_det}\n\n"
                f"📌 *Por favor verifica que la captura sea clara y emitida hacia el banco {banco_esperado}.*",
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id
            )

    except Exception as e:
        try: await msg_procesando.delete()
        except: pass
        await update.message.reply_text(f"⚠️ No se pudo procesar la imagen del comprobante: {str(e)}", reply_to_message_id=update.message.message_id)

async def enviar_informe_final(bot, db, rec_tuple: tuple, motivo_trigger: str = "Fecha límite alcanzada"):
    """Envía el informe final de recaudación al profesor"""
    rec_id, profesor_id, grupo_id, concepto, monto_unitario, banco, cedula, telefono, fecha_limite, activa = rec_tuple[:10]
    monto_unitario = float(monto_unitario)

    try:
        chat_info = await bot.get_chat(grupo_id)
        nombre_grupo = chat_info.title
    except:
        nombre_grupo = f"Grupo ID {grupo_id}"

    pagos = db.obtener_pagos_recaudacion(rec_id)
    cant_estudiantes = len(pagos)
    total_recaudado = cant_estudiantes * monto_unitario

    detalle_list = []
    if pagos:
        for p in pagos:
            ref = f"#{p[3]}" if len(p) > 3 and p[3] else ""
            detalle_list.append(f"• ✅ {p[0]} {ref} ({p[1]})")
        detalle_str = "\n".join(detalle_list)
    else:
        detalle_str = "Ningún pago registrado."

    informe = (
        f"📋 *INFORME FINAL DE RECAUDACIÓN*\n"
        f"🔔 *Disparador:* {motivo_trigger}\n\n"
        f"📚 *Grupo:* {nombre_grupo}\n"
        f"📝 *Concepto:* {concepto}\n"
        f"💵 *Monto por estudiante:* Bs. {monto_unitario:,.2f}\n"
        f"💰 *Total Recaudado:* Bs. {total_recaudado:,.2f}\n"
        f"👥 *Estudiantes que pagaron:* {cant_estudiantes}\n"
        f"⏰ *Fecha límite:* {fecha_limite}\n\n"
        f"📜 *Detalle de comprobantes validados:*\n"
        f"{detalle_str}"
    )

    # Marcar recaudación como finalizada
    db.finalizar_recaudacion(rec_id)

    # Enviar al profesor
    try:
        await bot.send_message(profesor_id, informe, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ Error enviando informe final al profesor: {e}")

    # Notificar en el grupo que la recaudación ha finalizado
    try:
        await bot.send_message(
            grupo_id,
            f"🏁 *RECAUDACIÓN FINALIZADA — {concepto}*\n\n"
            f"La recaudación ha concluido ({motivo_trigger}).\n"
            f"👥 Total de comprobantes validados: {cant_estudiantes}\n"
            f"💵 Total acumulado: Bs. {total_recaudado:,.2f}\n\n"
            f"¡Gracias a todos los participantes!",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"⚠️ Error enviando mensaje de fin a grupo: {e}")

async def verificar_fechas_limite_job(context: ContextTypes.DEFAULT_TYPE):
    """Job periódico para verificar fechas límite de recaudaciones activas"""
    db = context.bot_data.get('db')
    if not db:
        return
    
    recaudaciones_activas = db.obtener_todas_recaudaciones_activas()
    ahora = datetime.now()

    for rec in recaudaciones_activas:
        fecha_limite_str = rec[8]
        try:
            dt_limite = None
            for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt_limite = datetime.strptime(fecha_limite_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if dt_limite and ahora >= dt_limite:
                await enviar_informe_final(context.bot, db, rec, motivo_trigger="Fecha límite alcanzada")

        except Exception as e:
            print(f"⚠️ Error en revisión de fecha límite para recaudación {rec[0]}: {e}")

async def consultar_recaudacion_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la información de la recaudación activa en el grupo al ejecutar /recaudacion"""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    db = context.bot_data['db']

    if chat_type == 'private':
        await update.message.reply_text(
            "📌 *El comando /recaudacion debe usarse dentro del grupo de tu materia* para consultar la información del cobro activo.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
        await update.message.reply_text(
            "⚠️ *No hay ninguna recaudación activa en este grupo en este momento.*\n\n"
            "El profesor aún no ha creado ni publicado un proceso de cobro para este grupo.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    rec_id, profesor_id, g_id, concepto, monto, banco, cedula, telefono, fecha_limite, activa = rec_tuple[:10]
    monto = float(monto)

    pagos = db.obtener_pagos_recaudacion(rec_id)
    total_pagados = len(pagos)

    mensaje_info = (
        f"💸 *RECAUDACIÓN ACTIVA DEL GRUPO*\n\n"
        f"📝 *Concepto:* {concepto}\n"
        f"💵 *Monto requerimiento:* Bs. {monto:,.2f}\n\n"
        f"💳 *DATOS DE PAGO MÓVIL (DESTINO):*\n"
        f"🏦 *Banco:* {banco}\n"
        f"🪪 *Cédula:* {cedula}\n"
        f"📱 *Teléfono:* {telefono}\n\n"
        f"⏰ *Fecha Límite:* {fecha_limite}\n"
        f"👥 *Pagos validados hasta ahora:* {total_pagados}\n\n"
        f"📷 *INSTRUCCIONES DE REGISTRO:*\n"
        f"Envía la captura de tu comprobante a este grupo (o usa el comando `/pago` adjuntando la imagen) para que la IA lo valide."
    )

    await update.message.reply_text(
        mensaje_info,
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

