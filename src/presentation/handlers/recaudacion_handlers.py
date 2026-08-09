from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json, re
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.presentation.auth_utils import verificar_pertenencia_grupo

gemini = GeminiAdapter()

async def iniciar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de creación de recaudación"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['creando_recaudacion'] = True
    context.user_data['recaudacion_datos'] = {}
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *CREAR RECAUDACIÓN*\n\n"
        "Dime los datos de la recaudación. Puedes escribirlo en un solo mensaje "
        "o por partes. Necesito:\n"
        "• 📝 Concepto\n• 💵 Monto (Bs.)\n• 🏦 Banco\n• 🪪 Cédula\n• 📱 Teléfono\n• ⏰ Fecha límite\n\n"
        "Ejemplo: \"Exámenes Unidad I, 120, Mercantil, 12345678, 04121234567, 15/07/2026 23:59\"",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

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
                f"✅ *¡RECAUDACIÓN COMPLETA!*\n\n"
                f"📝 *Concepto:* {datos_actuales['concepto']}\n"
                f"💵 *Monto:* Bs. {monto:,.2f}\n"
                f"🏦 *Banco:* {datos_actuales['banco']}\n"
                f"🪪 *Cédula:* {datos_actuales['cedula']}\n"
                f"📱 *Teléfono:* {datos_actuales['telefono']}\n"
                f"⏰ *Fecha límite:* {datos_actuales['fecha_limite']}\n\n"
                "¿Deseas enviar esta recaudación a un grupo?"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ Enviar a grupo", callback_data="confirmar_recaudacion"),
                    InlineKeyboardButton("🔄 Corregir", callback_data="menu_recaudacion")
                ],
                [InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")]
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
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    
    await query.edit_message_text("📋 ¿A qué grupo deseas enviar esta recaudación?", reply_markup=InlineKeyboardMarkup(keyboard))

async def enviar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía la recaudación al grupo"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    chat_id = int(query.data.replace("enviar_recaudacion_", ""))
    datos = context.user_data.get('recaudacion_datos', {})

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return

    monto = float(str(datos['monto']).replace(',', '.'))
    db.crear_recaudacion(query.from_user.id, chat_id, str(datos['concepto']), monto, str(datos['banco']), str(datos['cedula']), str(datos['telefono']), str(datos['fecha_limite']))
    
    mensaje = (
        f"💸 *RECAUDACIÓN*\n\n📝 Concepto: {datos['concepto']}\n💵 Monto: Bs. {monto:,.2f}\n\n"
        f"*Datos Pago Móvil:*\n🏦 Banco: {datos['banco']}\n🪪 Cédula: {datos['cedula']}\n📱 Teléfono: {datos['telefono']}\n\n"
        f"⏰ Fecha límite: {datos['fecha_limite']}"
    )
    
    msg_enviado = await context.bot.send_message(chat_id, mensaje, parse_mode='Markdown')
    try: await context.bot.pin_chat_message(chat_id, msg_enviado.message_id)
    except: pass
    
    await query.edit_message_text("✅ Recaudación enviada exitosamente.")

async def validar_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida comprobante con Gemini Vision (CORREGIDO DESCARGA DE IMAGEN EN BYTES)"""
    if not update.message or not update.message.photo:
        return
    
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    image_bytes = await photo_file.download_as_bytearray()
    
    msg = await update.message.reply_text("🔍 Validando comprobante con visión IA...")
    try:
        resultado = gemini.analizar_comprobante_imagen(bytes(image_bytes))
        await msg.edit_text(f"✅ *Datos extraídos por IA:*\n```json\n{resultado}\n```", parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"⚠️ No se pudo procesar la imagen: {str(e)}")
