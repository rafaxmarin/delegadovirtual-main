from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from datetime import datetime
from gemini_handler import GeminiHandler
import json
import google.generativeai as genai # type: ignore

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
        "o por partes, como prefieras. Yo me encargo de organizar todo.\n\n"
        "Necesito saber:\n"
        "• 📝 Nombre o concepto\n"
        "• 💵 Monto por estudiante (Bs.)\n"
        "• 🏦 Banco\n"
        "• 🪪 Cédula\n"
        "• 📱 Teléfono\n"
        "• ⏰ Fecha y hora límite\n\n"
        "Ejemplo: \"Exámenes Unidad I, 120, Mercantil, "
        "12345678, 04121234567, 15/07/2026 23:59\"",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def procesar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa los datos de recaudación con IA de manera flexible"""
    
    # Verificar si estamos en modo recaudación
    if not context.user_data.get('creando_recaudacion'):
        return
    
    mensaje = update.message.text
    if not mensaje:
        return
    
    # Si el usuario quiere cancelar
    if mensaje.lower() in ['cancelar', 'cancel', 'salir', 'no']:
        context.user_data.pop('creando_recaudacion', None)
        context.user_data.pop('recaudacion_datos', None)
        await update.message.reply_text("✅ Recaudación cancelada. Usa /menu para volver.")
        return
    
    # 🟢 PASO 1: Mostrar que estamos procesando
    msg_procesando = await update.message.reply_text(
        "🔍 *Analizando tu mensaje...*",
        parse_mode='Markdown'
    )
    
    # 🟢 PASO 2: Simular escritura (el bot aparece "escribiendo...")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Obtener datos actuales
        datos_actuales = context.user_data.get('recaudacion_datos', {})
        
        # Actualizar mensaje de progreso
        await msg_procesando.edit_text(
            "🤖 *Consultando con la IA...*",
            parse_mode='Markdown'
        )
        
        # Prompt para Gemini
        prompt = f"""
        Analiza el siguiente mensaje y extrae información de recaudación.
        
        Mensaje del profesor: "{mensaje}"
        
        Datos que ya tenemos: {json.dumps(datos_actuales, ensure_ascii=False)}
        
        Identifica estos campos si aparecen:
        - concepto: nombre o motivo de la recaudación
        - monto: cantidad en bolívares (solo el número)
        - banco: nombre del banco
        - cedula: número de cédula
        - telefono: número de teléfono
        - fecha_limite: fecha y hora límite
        
        Responde EXCLUSIVAMENTE en JSON:
        {{"concepto": "...", "monto": 0, "banco": "...", "cedula": "...", "telefono": "...", "fecha_limite": "..."}}
        Si un campo no aparece, usa "no_encontrado".
        """
        
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        resultado = response.text.strip()
        
        # Actualizar mensaje
        await msg_procesando.edit_text(
            "📊 *Organizando información...*",
            parse_mode='Markdown'
        )
        
        # Limpiar respuesta
        resultado = resultado.replace('```json', '').replace('```', '').strip()
        
        # Intentar parsear JSON
        try:
            datos_nuevos = json.loads(resultado)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', resultado, re.DOTALL)
            if json_match:
                datos_nuevos = json.loads(json_match.group())
            else:
                raise Exception("No se pudo interpretar la respuesta")
        
        # Combinar datos
        for clave, valor in datos_nuevos.items():
            if valor and valor != "no_encontrado" and valor != 0:
                datos_actuales[clave] = valor
        
        context.user_data['recaudacion_datos'] = datos_actuales
        
        # Verificar campos
        campos = ['concepto', 'monto', 'banco', 'cedula', 'telefono', 'fecha_limite']
        completos = []
        faltantes = []
        
        for campo in campos:
            valor = datos_actuales.get(campo)
            if valor and valor != "no_encontrado" and valor != 0:
                completos.append(campo)
            else:
                faltantes.append(campo)
        
        # Eliminar mensaje de procesando
        await msg_procesando.delete()
        
        if faltantes:
            # Mostrar progreso
            nombres_campos = {
                'concepto': 'Concepto',
                'monto': 'Monto por estudiante',
                'banco': 'Banco',
                'cedula': 'Cédula',
                'telefono': 'Teléfono',
                'fecha_limite': 'Fecha límite'
            }
            
            mensaje_progreso = "📊 *PROGRESO DE RECAUDACIÓN*\n\n"
            
            for campo in campos:
                nombre = nombres_campos.get(campo, campo)
                if campo in completos:
                    valor = datos_actuales.get(campo)
                    if campo == 'monto':
                        mensaje_progreso += f"✅ {nombre}: Bs. {valor}\n"
                    else:
                        mensaje_progreso += f"✅ {nombre}: {valor}\n"
                else:
                    mensaje_progreso += f"⬜ {nombre}: *PENDIENTE*\n"
            
            # Sugerencias
            sugerencias = []
            if 'monto' in faltantes:
                sugerencias.append("• El monto (ej: 120)")
            if 'banco' in faltantes:
                sugerencias.append("• El banco (Mercantil, Banesco, etc.)")
            if 'cedula' in faltantes:
                sugerencias.append("• La cédula del beneficiario")
            if 'telefono' in faltantes:
                sugerencias.append("• El teléfono (0412...)")
            if 'fecha_limite' in faltantes:
                sugerencias.append("• La fecha límite (ej: 22/07/2026 20:30)")
            if 'concepto' in faltantes:
                sugerencias.append("• El nombre de la recaudación")
            
            if sugerencias:
                mensaje_progreso += f"\n💡 *Falta proporcionar:*\n" + "\n".join(sugerencias)
            
            mensaje_progreso += "\n\n✏️ Puedes enviarme los datos faltantes en otro mensaje."
            
            await update.message.reply_text(
                mensaje_progreso,
                parse_mode='Markdown'
            )
        else:
            # ¡Todo completo!
            context.user_data['creando_recaudacion'] = False
            
            monto = datos_actuales['monto']
            if isinstance(monto, str):
                monto = monto.replace(',', '.')
            monto = float(monto)
            
            resumen = (
                f"✅ *¡RECAUDACIÓN COMPLETA!*\n\n"
                f"📝 *Concepto:* {datos_actuales['concepto']}\n"
                f"💵 *Monto por estudiante:* Bs. {monto:,.2f}\n"
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
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                resumen,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    except Exception as e:
        # Eliminar mensaje de procesando
        try:
            await msg_procesando.delete()
        except:
            pass
        
        # Mensaje de error claro
        await update.message.reply_text(
            f"⚠️ *NO PUDE PROCESAR LOS DATOS*\n\n"
            f"Posibles causas:\n"
            f"• Formato de datos confuso\n"
            f"• Información incompleta\n"
            f"• Error de conexión con la IA\n\n"
            f"💡 *Sugerencia:* Intenta con este formato:\n"
            f"\"Concepto: Exámenes, Monto: 120, Banco: Mercantil, "
            f"Cédula: 12345678, Teléfono: 04121234567, "
            f"Fecha: 22/07/2026 20:30\"\n\n"
            f"O escribe /menu para empezar de nuevo.",
            parse_mode='Markdown'
        )

async def confirmar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma la recaudación y muestra los grupos"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    datos = context.user_data.get('recaudacion_datos', {})
    
    if not datos:
        await query.edit_message_text("❌ No hay datos de recaudación. Inicia de nuevo con /menu")
        return
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text(
            "❌ No tienes grupos registrados.\n"
            "Agrega el bot a un grupo de Telegram primero."
        )
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"enviar_recaudacion_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 ¿A qué grupo deseas enviar esta recaudación?",
        reply_markup=reply_markup
    )

async def enviar_recaudacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía la recaudación al grupo seleccionado"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    chat_id = int(query.data.replace("enviar_recaudacion_", ""))
    datos = context.user_data.get('recaudacion_datos', {})
    
    try:
        monto = float(str(datos['monto']).replace(',', '.'))
    except:
        await query.edit_message_text("❌ Error: El monto no es válido.")
        return
    
    # Crear en BD
    recaudacion_id = db.crear_recaudacion(
        user.id, chat_id, str(datos['concepto']), monto,
        str(datos['banco']), str(datos['cedula']), str(datos['telefono']),
        str(datos['fecha_limite'])
    )
    
    mensaje = (
        f"💸 *RECAUDACIÓN*\n\n"
        f"📝 Concepto: {datos['concepto']}\n"
        f"💵 Monto por estudiante: Bs. {monto:,.2f}\n\n"
        f"*Datos del beneficiario (Pago Móvil):*\n"
        f"🏦 Banco: {datos['banco']}\n"
        f"🪪 Cédula: {datos['cedula']}\n"
        f"📱 Teléfono: {datos['telefono']}\n\n"
        f"⏰ Fecha límite: {datos['fecha_limite']}\n\n"
        f"⚠️ *IMPORTANTE:* Al realizar el pago, compartan "
        f"por este grupo una foto del comprobante donde se vea:\n"
        f"• Nombre y apellido del estudiante (en el concepto)\n"
        f"• Fecha y hora del pago\n"
        f"• Datos del beneficiario"
    )
    
    try:
        msg_enviado = await context.bot.send_message(
            chat_id, mensaje, parse_mode='Markdown'
        )
        await context.bot.pin_chat_message(chat_id, msg_enviado.message_id)
        
        await query.edit_message_text(
            f"✅ Recaudación enviada exitosamente.\n"
            f"Concepto: {datos['concepto']}\n"
            f"Grupo: {chat_id}"
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error al enviar: {str(e)}\n\n"
            "Verifica que el bot tenga permisos en el grupo."
        )

# Mantener estas funciones igual
async def validar_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida comprobantes de pago"""
    chat = update.effective_chat
    db = context.bot_data['db']
    
    if chat.type not in ['group', 'supergroup']:
        return
    
    if not update.message.photo:
        return
    
    await update.message.reply_text(
        "🔍 Validando comprobante...\n"
        "Esta función estará completamente disponible pronto."
    )

async def actualizar_lista_pagos(context, recaudacion_id, chat_id):
    """Actualiza la lista de pagos"""
    pass  # Se implementará completo después