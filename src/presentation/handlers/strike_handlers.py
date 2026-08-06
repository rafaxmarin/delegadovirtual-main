from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from src.infrastructure.ai.gemini_adapter import GeminiAdapter

gemini = GeminiAdapter()

async def control_strikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel de control de strikes"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    strikes = db.obtener_strikes_profesor(user.id)
    
    if not strikes:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚡ *CONTROL DE STRIKES*\n\n"
            "No hay estudiantes con strikes registrados.\n\n"
            "El bot monitorea automáticamente los grupos en busca de:\n"
            "• Malas palabras u obscenidades\n"
            "• Lenguaje ofensivo\n"
            "• Material inapropiado\n"
            "• Contenido no educativo",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    mensaje = "⚡ *CONTROL DE STRIKES*\n\n"
    keyboard = []
    for estudiante_nombre, grupo_id, grupo_nombre, total in strikes:
        emoji = "⚠️" if total < 3 else "🚫"
        if total >= 10:
            emoji = "🔴"
        
        mensaje += f"{emoji} *{estudiante_nombre}* - {grupo_nombre}: {total} strikes\n"
        keyboard.append([
            InlineKeyboardButton(
                f"📋 Ver {estudiante_nombre}",
                callback_data=f"ver_strikes_{grupo_id}_{estudiante_nombre}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ver_historial_strikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el historial de strikes de un estudiante (CORREGIDO MÉTODO DB Y INDENTACIÓN)"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    data = query.data.replace("ver_strikes_", "")
    partes = data.split("_", 1)
    grupo_id = int(partes[0])
    estudiante_nombre = partes[1]
    
    historial = db.obtener_historial_strikes_por_nombre(estudiante_nombre, grupo_id)
    total = len(historial)
    
    mensaje = (
        f"👤 *{estudiante_nombre}*\n"
        f"Total de strikes: {total}\n\n"
        f"📋 *HISTORIAL:*\n"
    )
    
    for i, (motivo, fecha) in enumerate(historial, 1):
        mensaje += f"{i}. {fecha}: {motivo}\n"
    
    keyboard = [
        [
            InlineKeyboardButton(
                "🚫 Eliminar del grupo",
                callback_data=f"eliminar_estudiante_strikes_{grupo_id}_{estudiante_nombre}"
            )
        ],
        [InlineKeyboardButton("🔙 Volver", callback_data="menu_strikes")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def monitorear_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitorea mensajes en grupos (CORREGIDO ES_GRUPO_REGISTRADO Y CHATPERMISSIONS)"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if chat.type not in ['group', 'supergroup']:
        return
    
    if not message:
        return
    
    # 🔴 CORRECCIÓN: Verificar si el grupo está registrado correctamente
    if not db.es_grupo_registrado(chat.id):
        return
    
    if user.is_bot:
        return
    
    contenido = ""
    if message.text:
        contenido = message.text
    elif message.caption:
        contenido = message.caption
    elif message.photo or message.video or message.document:
        contenido = "[Contenido multimedia]"
    
    if not contenido:
        return
    
    try:
        resultado = gemini.detectar_contenido_inapropiado(contenido)
        
        if resultado.startswith("SI"):
            motivo = resultado.replace("SI - ", "") if " - " in resultado else "Contenido inapropiado"
            strikes_actuales = db.obtener_strikes_estudiante(user.id, chat.id)
            nuevo_strike = strikes_actuales + 1
            
            db.agregar_strike(user.id, user.full_name, chat.id, motivo)
            
            if nuevo_strike == 1:
                await message.reply_text(
                    f"⚠️ *STRIKE 1/3 - {user.full_name}*\n"
                    f"Motivo: {motivo}\n"
                    "Por favor, mantén el respeto en el grupo.",
                    parse_mode='Markdown'
                )
            elif nuevo_strike == 2:
                await message.reply_text(
                    f"⚠️ *STRIKE 2/3 - {user.full_name}*\n"
                    f"Motivo: {motivo}\n"
                    "Último aviso. Un strike más y no podrás escribir por 24 horas.",
                    parse_mode='Markdown'
                )
            elif nuevo_strike >= 3:
                try:
                    # 🔴 CORRECCIÓN: Usar ChatPermissions en lugar de un diccionario plano
                    permisos = ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False
                    )
                    await context.bot.restrict_chat_member(
                        chat.id,
                        user.id,
                        permissions=permisos,
                        until_date=datetime.now() + timedelta(hours=24)
                    )
                    
                    await message.reply_text(
                        f"🚫 *RESTRICCIÓN - {user.full_name}*\n"
                        f"Has alcanzado los 3 strikes.\n"
                        "No podrás escribir en este grupo durante 24 horas.",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    await message.reply_text(
                        "⚠️ El estudiante ha alcanzado 3 strikes pero no se pudo restringir. "
                        "Verifica que el bot tenga permisos de administrador."
                    )
            
    except Exception:
        pass
