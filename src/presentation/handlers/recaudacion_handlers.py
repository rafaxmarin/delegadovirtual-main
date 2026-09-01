from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json, re, os
from datetime import datetime
from src.infrastructure.ai.ai_service import AIService
from src.presentation.auth_utils import verificar_pertenencia_grupo
from src.infrastructure.documents.pdf_exporter import generar_pdf_reporte_recaudacion

gemini = AIService()

def obtener_codigo_banco(banco_str: str) -> str:
    """Extrae o convierte el nombre del banco a su código de 4 dígitos para Pago Móvil en Venezuela"""
    if not banco_str:
        return ""
    import re
    match = re.search(r'\b\d{4}\b', banco_str)
    if match:
        return match.group()

    banco_clean = banco_str.lower()
    mapa_bancos = {
        'mercantil': '0105',
        'venezuela': '0102',
        'bdv': '0102',
        'banesco': '0134',
        'provincial': '0108',
        'bbva': '0108',
        'bnc': '0191',
        'credito': '0191',
        'bancaribe': '0114',
        'exterior': '0115',
        'plaza': '0138',
        'sofitasa': '0137',
        '100%': '0156',
        'del sur': '0157',
        'tesoro': '0163',
        'bancamiga': '0172',
        'bancrecer': '0168',
        'mi banco': '0169',
        'activo': '0171',
        'bicentenario': '0175',
        'banfanb': '0177',
    }
    for clave, codigo in mapa_bancos.items():
        if clave in banco_clean:
            return codigo
    return banco_str.strip()

def limpiar_cedula(cedula_str: str) -> str:
    """Limpia puntos, comas y espacios de la cédula o RIF"""
    if not cedula_str:
        return ""
    import re
    return re.sub(r'[\.,\s]', '', cedula_str.strip())

def limpiar_telefono(telefono_str: str) -> str:
    """Limpia guiones, espacios y paréntesis dejando únicamente los dígitos"""
    if not telefono_str:
        return ""
    import re
    return re.sub(r'[^\d]', '', telefono_str.strip())

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
        resultado = gemini.extraer_datos_recaudacion(mensaje, datos_actuales)
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
    
    cod_banco = obtener_codigo_banco(str(datos['banco']))
    ced_clean = limpiar_cedula(str(datos['cedula']))
    tel_clean = limpiar_telefono(str(datos['telefono']))
    monto_clean = f"{monto:.2f}"

    mensaje_anuncio = (
        f"💸 *NUEVA RECAUDACIÓN AUTORIZADA*\n\n"
        f"📝 *Concepto:* {datos['concepto']}\n"
        f"💵 *Monto requerimiento:* Bs. {monto:,.2f}\n\n"
        f"💳 *DATOS PARA PAGO MÓVIL (DESTINO):*\n"
        f"1️⃣ *Código de Banco ({datos['banco']}):*\n`{cod_banco}`\n"
        f"2️⃣ *Cédula / RIF:*\n`{ced_clean}`\n"
        f"3️⃣ *Teléfono:*\n`{tel_clean}`\n"
        f"4️⃣ *Monto:*\n`{monto_clean}`\n\n"
        f"⏰ *Fecha Límite:* {datos['fecha_limite']}\n\n"
        f"📌 *INSTRUCCIONES DE REGISTRO DE PAGO:*\n"
        f"• 📲 *Pago Móvil:* Escribe en este grupo el comando `/pago` con tu número de referencia y nombres:\n"
        f"  👉 `/pago 564654654646564 Alan Brito y Solomeo Paredes`\n"
        f"  👉 O si es solo para ti: `/pago 564654654646564`\n"
        f"• 💵 *Pago en Efectivo:* Si le pagaste en físico al profesor, ejecuta `/efectivo` en este grupo."
    )
    
    keyboard_anuncio = [[InlineKeyboardButton("📋 Copiar Datos de Pago", callback_data=f"copiar_datos_pago_{rec_id}")]]
    msg_anuncio = await context.bot.send_message(
        chat_id,
        mensaje_anuncio,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard_anuncio)
    )
    try: await context.bot.pin_chat_message(chat_id, msg_anuncio.message_id)
    except: pass

    await query.edit_message_text("✅ Recaudación enviada y publicada exitosamente en el grupo.")

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
            nombre_est = p[0]
            fecha_p = p[1]
            ref = f"#{p[3]}" if len(p) > 3 and p[3] else "S/R"
            rep_nom = p[5] if len(p) > 5 and p[5] else ""
            rep_ced = p[6] if len(p) > 6 and p[6] else ""

            rep_info = ""
            if rep_nom and rep_nom.lower() != nombre_est.lower():
                ced_str = f" (CI: {rep_ced})" if rep_ced else ""
                rep_info = f" _[Reportó: {rep_nom}{ced_str}]_"
            elif rep_ced:
                rep_info = f" _(CI: {rep_ced})_"

            lineas_pagos.append(f"• ✅ *{nombre_est}* — Ref: `{ref}`{rep_info} ({fecha_p})")
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

    keyboard = [
        [InlineKeyboardButton("📄 Descargar Reporte en PDF", callback_data=f"descargar_pdf_rec_{rec_id}")],
        [InlineKeyboardButton("🔙 Volver a la lista de grupos", callback_data="ver_reporte_recaudacion_menu")]
    ]
    await query.edit_message_text(reporte_texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def descargar_pdf_recaudacion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera y despacha el archivo PDF oficial con la tabla detallada de pagos y referencias bancarias"""
    query = update.callback_query
    if not query:
        return

    await query.answer("📄 Generando documento PDF...")

    rec_id = int(query.data.replace("descargar_pdf_rec_", ""))
    db = context.bot_data['db']

    # Obtener recaudación
    db.cursor.execute('SELECT * FROM recaudaciones WHERE id = ?', (rec_id,))
    rec_tuple = db.cursor.fetchone()
    if not rec_tuple:
        await query.message.reply_text("❌ No se encontró la recaudación solicitada.")
        return

    rec_id, profesor_id, g_id, concepto, monto_unitario, banco, cedula, telefono, fecha_limite, activa = rec_tuple[:10]
    
    # Obtener nombre del grupo
    try:
        chat_info = await context.bot.get_chat(g_id)
        nombre_grupo = chat_info.title
    except Exception:
        nombre_grupo = f"Grupo ID {g_id}"

    pagos = db.obtener_pagos_recaudacion(rec_id)
    cant_estudiantes = len(pagos)
    monto_unitario = float(monto_unitario)
    total_recaudado = cant_estudiantes * monto_unitario
    estado_str = "Activa" if activa == 1 else "Finalizada"

    datos_rec = {
        'concepto': concepto,
        'nombre_grupo': nombre_grupo,
        'monto_unitario': monto_unitario,
        'total_recaudado': total_recaudado,
        'cant_estudiantes': cant_estudiantes,
        'banco': banco,
        'fecha_limite': fecha_limite,
        'estado': estado_str,
        'fecha_generacion': datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    try:
        pdf_path = generar_pdf_reporte_recaudacion(datos_rec, pagos)
        filename_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', concepto)[:30]
        filename = f"Reporte_Pagos_{filename_clean}.pdf"

        with open(pdf_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=f,
                filename=filename,
                caption=f"📄 *Reporte de Recaudación: {concepto}*\n📊 Total de pagos registrados: {cant_estudiantes}\n💰 Monto recaudado: Bs. {total_recaudado:,.2f}",
                parse_mode='Markdown'
            )
        try: os.remove(pdf_path)
        except: pass
    except Exception as e:
        print(f"⚠️ Error generando o enviando PDF de recaudación: {e}")
        await query.message.reply_text(f"⚠️ Ocurrió un error al generar el PDF: {str(e)}")

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

def parsear_comando_pago(texto: str) -> Tuple[Optional[str], List[str]]:
    """
    Extrae el número de referencia y la lista de nombres de estudiantes de un comando /pago.
    Ejemplos:
    /pago 564654654646564 Alan Brito y Solomeo Paredes -> ('564654654646564', ['Alan Brito', 'Solomeo Paredes'])
    /pago 564654654646564 Alan Brito -> ('564654654646564', ['Alan Brito'])
    /pago 564654654646564 -> ('564654654646564', [])
    """
    if not texto:
        return None, []
    
    t = re.sub(r'^/pago(?:@\w+)?\s*', '', texto.strip(), flags=re.IGNORECASE)
    if not t:
        return None, []
    
    # Buscar número de referencia (al menos 4 dígitos)
    match_ref = re.search(r'(?:ref(?:\.|:)?|#)?\s*(\d{4,30})', t, flags=re.IGNORECASE)
    if not match_ref:
        return None, []
    
    referencia = match_ref.group(1)
    resto = t[:match_ref.start()] + " " + t[match_ref.end():]
    resto = resto.strip(' .,-:_')
    
    if not resto:
        return referencia, []
    
    # Separar nombres usando ' y ', ' e ', ',', ';', '/' o salto de línea
    partes = re.split(r'\s*(?:,|;|\/|\n|\s+[yeEY]\s+)\s*', resto)
    nombres = []
    for p in partes:
        p_clean = p.strip(' .,-:_')
        if p_clean and re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', p_clean):
            nombres.append(p_clean)
    
    return referencia, nombres

async def validar_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el comando /pago por referencia de texto o validación con imagen"""
    if not update.message:
        return
    
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    user = update.effective_user
    estudiante_nombre = (user.full_name or (f"@{user.username}" if user.username else "Estudiante")).strip()

    # Si se envía por chat privado
    if chat_type == 'private':
        await update.message.reply_text(
            "📌 *Por favor reporta tu pago directamente en el grupo de tu materia* donde está el bot usando `/pago <referencia> [nombres]`.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    db = context.bot_data['db']

    # Solo procesar si el grupo tiene una recaudación activa
    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
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

    # Datos del usuario de Telegram que reporta
    reportado_por_id = user.id
    reportado_por_nombre = estudiante_nombre
    reportado_por_cedula = db.obtener_cedula_usuario(chat_id, user.id, estudiante_nombre) or ""

    # Detectar si hay imagen adjunta o respondida
    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
    elif update.message.document:
        doc = update.message.document
        mime = doc.mime_type or ""
        fname = doc.file_name or ""
        if mime.startswith('image/') or fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.heic')):
            photo_file_id = doc.file_id
    elif update.message.reply_to_message:
        reply_msg = update.message.reply_to_message
        if reply_msg.photo:
            photo_file_id = reply_msg.photo[-1].file_id
        elif reply_msg.document:
            doc = reply_msg.document
            mime = doc.mime_type or ""
            fname = doc.file_name or ""
            if mime.startswith('image/') or fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.heic')):
                photo_file_id = doc.file_id

    # CASO 1: Reporte por IMAGEN / CAPTURA (Visión IA de respaldo)
    if photo_file_id:
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
                    numero_verificacion=num_ref,
                    reportado_por_id=reportado_por_id,
                    reportado_por_nombre=reportado_por_nombre,
                    reportado_por_cedula=reportado_por_cedula
                )

                det_ced = f" (CI: {reportado_por_cedula})" if reportado_por_cedula else ""
                await update.message.reply_text(
                    f"✅ *¡PAGO VÁLIDO Y REGISTRADO!*\n\n"
                    f"👤 *Estudiante:* {estudiante_nombre}{det_ced}\n"
                    f"🔢 *Ref / Comprobante:* #{num_ref}\n"
                    f"🏦 *Banco Destino:* {banco_det}\n"
                    f"💵 *Monto:* Bs. {monto_esperado:,.2f}\n"
                    f"📅 *Fecha:* {fecha_pago}",
                    parse_mode='Markdown',
                    reply_to_message_id=update.message.message_id
                )

                await verificar_y_enviar_fin_recaudacion(context.bot, chat_id, db, rec_tuple)
            else:
                motivo = evaluacion.get('motivo_rechazo', 'La captura no cumple con los requisitos esperados.')
                banco_det = evaluacion.get('banco_detectado', 'Desconocido')

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
        return

    # CASO 2: Reporte por TEXTO / COMANDO con NÚMERO DE REFERENCIA
    texto_msg = update.message.text or update.message.caption or ""
    if not texto_msg and context.args:
        texto_msg = "/pago " + " ".join(context.args)

    referencia, lista_estudiantes = parsear_comando_pago(texto_msg)

    if not referencia:
        await update.message.reply_text(
            "📌 *FORMATO DEL COMANDO /pago*\n\n"
            "Para reportar tu pago móvil, escribe el comando con la referencia y el/los nombres de los estudiantes:\n\n"
            "👉 `/pago <número de referencia> [nombres]`\n\n"
            "• *Pago para ti mismo:*\n"
            "  `/pago 564654654646564`\n"
            "• *Pago individual con nombre:*\n"
            "  `/pago 564654654646564 Alan Brito`\n"
            "• *Pago múltiple:*\n"
            "  `/pago 564654654646564 Alan Brito y Solomeo Paredes`",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    # Si no se colocaron nombres explícitos, se asigna al propio usuario de Telegram
    if not lista_estudiantes:
        lista_estudiantes = [estudiante_nombre]

    fecha_pago = datetime.now().strftime("%d/%m/%Y %H:%M")
    registrados = []
    ya_pagaron = []

    for est_nom in lista_estudiantes:
        est_id = user.id if (len(lista_estudiantes) == 1 and (est_nom.lower() == estudiante_nombre.lower() or not context.args)) else None
        
        if db.estudiante_ya_pago(rec_id, est_id, est_nom):
            ya_pagaron.append(est_nom)
        else:
            db.registrar_pago(
                recaudacion_id=rec_id,
                estudiante_nombre=est_nom,
                fecha_pago=fecha_pago,
                estudiante_id=est_id,
                numero_verificacion=referencia,
                reportado_por_id=reportado_por_id,
                reportado_por_nombre=reportado_por_nombre,
                reportado_por_cedula=reportado_por_cedula
            )
            registrados.append(est_nom)

    # Armar mensaje de respuesta
    det_cedula = f" (CI: {reportado_por_cedula})" if reportado_por_cedula else ""
    msg_resp = []

    if registrados:
        if len(registrados) == 1:
            msg_resp.append(
                f"✅ *¡PAGO REGISTRADO EXITOSAMENTE!*\n\n"
                f"👤 *Estudiante:* {registrados[0]}\n"
                f"🔢 *Ref:* #{referencia}\n"
                f"💵 *Monto:* Bs. {monto_esperado:,.2f}\n"
                f"📅 *Fecha:* {fecha_pago}\n"
                f"📩 *Reportado por:* {reportado_por_nombre}{det_cedula}"
            )
        else:
            lista_noms = "\n".join([f"  • {nom}" for nom in registrados])
            total_monto = len(registrados) * monto_esperado
            msg_resp.append(
                f"✅ *¡PAGO MÚLTIPLE REGISTRADO EXITOSAMENTE!*\n\n"
                f"👥 *Estudiantes cubiertos ({len(registrados)}):*\n{lista_noms}\n\n"
                f"🔢 *Ref:* #{referencia}\n"
                f"💵 *Monto total:* Bs. {total_monto:,.2f} (Bs. {monto_esperado:,.2f} c/u)\n"
                f"📅 *Fecha:* {fecha_pago}\n"
                f"📩 *Reportado por:* {reportado_por_nombre}{det_cedula}"
            )

    if ya_pagaron:
        noms_ya = ", ".join(ya_pagaron)
        msg_resp.append(f"⚠️ *Atención:* {noms_ya} ya tenía(n) un pago previamente registrado en esta recaudación.")

    await update.message.reply_text(
        "\n\n".join(msg_resp),
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

    # Verificar si se completaron los pagos
    if registrados:
        await verificar_y_enviar_fin_recaudacion(context.bot, chat_id, db, rec_tuple)

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
            nombre_est = p[0]
            fecha_p = p[1]
            ref = f"#{p[3]}" if len(p) > 3 and p[3] else "S/R"
            rep_nom = p[5] if len(p) > 5 and p[5] else ""
            rep_ced = p[6] if len(p) > 6 and p[6] else ""

            rep_info = ""
            if rep_nom and rep_nom.lower() != nombre_est.lower():
                ced_str = f" (CI: {rep_ced})" if rep_ced else ""
                rep_info = f" [Reportó: {rep_nom}{ced_str}]"
            elif rep_ced:
                rep_info = f" (CI: {rep_ced})"

            detalle_list.append(f"• ✅ {nombre_est} — Ref: {ref}{rep_info} ({fecha_p})")
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

    # Enviar informe texto al profesor
    try:
        await bot.send_message(profesor_id, informe, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ Error enviando informe final al profesor: {e}")

    # Generar y enviar documento PDF al profesor
    try:
        datos_rec = {
            'concepto': concepto,
            'nombre_grupo': nombre_grupo,
            'monto_unitario': monto_unitario,
            'total_recaudado': total_recaudado,
            'cant_estudiantes': cant_estudiantes,
            'banco': banco,
            'fecha_limite': fecha_limite,
            'estado': 'Finalizada',
            'fecha_generacion': datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        pdf_path = generar_pdf_reporte_recaudacion(datos_rec, pagos)
        filename_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', concepto)[:30]
        filename = f"Informe_Final_{filename_clean}.pdf"
        with open(pdf_path, 'rb') as f:
            await bot.send_document(
                chat_id=profesor_id,
                document=f,
                filename=filename,
                caption=f"📄 *Documento Oficial en PDF — {concepto}*",
                parse_mode='Markdown'
            )
        try: os.remove(pdf_path)
        except: pass
    except Exception as e:
        print(f"⚠️ Error enviando PDF de informe final: {e}")

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

    cod_banco = obtener_codigo_banco(str(banco))
    ced_clean = limpiar_cedula(str(cedula))
    tel_clean = limpiar_telefono(str(telefono))
    monto_clean = f"{monto:.2f}"
    total_pagados = db.contar_pagos(rec_id)

    mensaje_info = (
        f"💸 *RECAUDACIÓN ACTIVA DEL GRUPO*\n\n"
        f"📝 *Concepto:* {concepto}\n"
        f"💵 *Monto requerimiento:* Bs. {monto:,.2f}\n\n"
        f"💳 *DATOS PARA PAGO MÓVIL (DESTINO):*\n"
        f"1️⃣ *Código de Banco ({banco}):*\n`{cod_banco}`\n"
        f"2️⃣ *Cédula / RIF:*\n`{ced_clean}`\n"
        f"3️⃣ *Teléfono:*\n`{tel_clean}`\n"
        f"4️⃣ *Monto:*\n`{monto_clean}`\n\n"
        f"⏰ *Fecha Límite:* {fecha_limite}\n"
        f"👥 *Pagos validados hasta ahora:* {total_pagados}\n\n"
        f"📌 *INSTRUCCIONES DE REGISTRO DE PAGO:*\n"
        f"• 📲 *Pago Móvil:* Escribe en este grupo el comando `/pago` con tu referencia y nombres:\n"
        f"  👉 `/pago 564654654646564 Alan Brito y Solomeo Paredes`\n"
        f"  👉 O si es individual: `/pago 564654654646564`\n"
        f"• 💵 *Pago en Efectivo:* Si pagaste en físico al profesor, ejecuta `/efectivo` en este grupo."
    )

    keyboard = [[InlineKeyboardButton("📋 Copiar Datos de Pago", callback_data=f"copiar_datos_pago_{rec_id}")]]
    await update.message.reply_text(
        mensaje_info,
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def copiar_datos_pago_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía los datos de pago formato código ordenados para Pago Móvil (Código Banco, RIF/Cédula, Teléfono, Monto)"""
    query = update.callback_query
    if not query:
        return

    await query.answer("📋 Toca cada valor monoespaciado para copiarlo a tu banco.")

    rec_id = int(query.data.replace("copiar_datos_pago_", ""))
    db = context.bot_data['db']

    db.cursor.execute('SELECT concepto, monto, banco, cedula, telefono FROM recaudaciones WHERE id = ?', (rec_id,))
    row = db.cursor.fetchone()
    if not row:
        return

    concepto, monto, banco, cedula, telefono = row
    cod_banco = obtener_codigo_banco(str(banco))
    ced_clean = limpiar_cedula(str(cedula))
    tel_clean = limpiar_telefono(str(telefono))
    monto_clean = f"{float(monto):.2f}"

    msg_copiar = (
        f"```\n"
        f"{cod_banco}\n"
        f"{ced_clean}\n"
        f"{tel_clean}\n"
        f"{monto_clean}\n"
        f"```"
    )

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg_copiar,
            parse_mode='Markdown',
            reply_to_message_id=query.message.message_id if query.message else None
        )
    except Exception as e:
        print(f"⚠️ Error enviando datos copiables de pago: {e}")

async def verificar_y_enviar_fin_recaudacion(bot, chat_id: int, db, rec_tuple: tuple):
    """Verifica si ya pagaron todos los estudiantes del grupo para enviar el informe final al profesor"""
    rec_id = rec_tuple[0]
    total_pagos = db.contar_pagos(rec_id)
    try:
        cant_miembros = await bot.get_chat_member_count(chat_id)
        # En grupos de Telegram, los miembros incluyen al bot y al profesor.
        estudiantes_esperados = max(1, cant_miembros - 2)
    except Exception as e:
        print(f"⚠️ No se pudo obtener la cantidad de miembros del grupo: {e}")
        estudiantes_esperados = None

    if estudiantes_esperados and total_pagos >= estudiantes_esperados:
        await enviar_informe_final(bot, db, rec_tuple, motivo_trigger="Todos los pagos han sido realizados")

async def registrar_pago_efectivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra un pago en efectivo para la recaudación activa del grupo (Comando /efectivo)"""
    if not update.message:
        return
    
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    user = update.effective_user
    db = context.bot_data['db']

    if chat_type == 'private':
        await update.message.reply_text(
            "📌 *El comando /efectivo debe ejecutarse dentro del grupo de tu materia* para registrar el pago en efectivo.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    rec_tuple = db.obtener_recaudacion_activa(chat_id)
    if not rec_tuple:
        await update.message.reply_text(
            "⚠️ *No hay ninguna recaudación activa en este grupo en este momento.*",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    rec_id = rec_tuple[0]
    concepto = rec_tuple[3]
    monto_esperado = float(rec_tuple[4])

    # Determinar a qué estudiante se le asigna el pago
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        estudiante_id = target_user.id
        estudiante_nombre = target_user.full_name or (f"@{target_user.username}" if target_user.username else "Estudiante")
    elif context.args:
        estudiante_id = None
        estudiante_nombre = " ".join(context.args).strip()
    else:
        estudiante_id = user.id
        estudiante_nombre = user.full_name or (f"@{user.username}" if user.username else "Estudiante")

    if db.estudiante_ya_pago(rec_id, estudiante_id, estudiante_nombre):
        await update.message.reply_text(
            f"⚠️ *{estudiante_nombre}*, ya tienes un pago registrado para la recaudación *{concepto}*.",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        return

    fecha_pago = datetime.now().strftime("%d/%m/%Y %H:%M")
    num_ref = "EFECTIVO"

    reportado_por_id = user.id
    reportado_por_nombre = (user.full_name or f"@{user.username}" or "Usuario").strip()
    reportado_por_cedula = db.obtener_cedula_usuario(chat_id, user.id, reportado_por_nombre) or ""

    db.registrar_pago(
        recaudacion_id=rec_id,
        estudiante_nombre=estudiante_nombre,
        fecha_pago=fecha_pago,
        estudiante_id=estudiante_id,
        numero_verificacion=num_ref,
        reportado_por_id=reportado_por_id,
        reportado_por_nombre=reportado_por_nombre,
        reportado_por_cedula=reportado_por_cedula
    )

    det_ced = f" (CI: {reportado_por_cedula})" if reportado_por_cedula else ""
    await update.message.reply_text(
        f"💵 *¡PAGO EN EFECTIVO REGISTRADO!*\n\n"
        f"👤 *Estudiante:* {estudiante_nombre}\n"
        f"🔢 *Ref:* #{num_ref}\n"
        f"💵 *Monto:* Bs. {monto_esperado:,.2f}\n"
        f"📅 *Fecha:* {fecha_pago}",
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

    await actualizar_lista_en_vivo(
        context.bot, chat_id, db, rec_id, concepto, monto_esperado, fecha_limite, mensaje_lista_id
    )

    await verificar_y_enviar_fin_recaudacion(context.bot, chat_id, db, rec_tuple)


