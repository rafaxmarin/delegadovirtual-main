from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from gemini_handler import GeminiHandler
import asyncio

async def control_strikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel de control de strikes"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    # Obtener estudiantes con strikes
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
    """Muestra el historial de strikes de un estudiante"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    # Parsear datos
    data = query.data.replace("ver_strikes_", "")
    partes = data.split("_", 1)
    grupo_id = int(partes[0])
    estudiante_nombre = partes[1]
    
    # Obtener historial
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

async def eliminar_estudiante_strikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina a un estudiante del grupo desde el panel de strikes"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("eliminar_estudiante_strikes_", "")
    partes = data.split("_", 1)
    grupo_id = int(partes[0])
    estudiante_nombre = partes[1]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"confirmar_eliminar_{grupo_id}_{estudiante_nombre}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="menu_strikes")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🚫 ¿Eliminar a *{estudiante_nombre}* del grupo?\n\n"
        "Esta acción no se puede deshacer.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def confirmar_eliminar_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma la eliminación del estudiante"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    data = query.data.replace("confirmar_eliminar_", "")
    partes = data.split("_", 1)
    grupo_id = int(partes[0])
    estudiante_nombre = partes[1]
    
    try:
        # Buscar al estudiante en el grupo
        # Nota: La API de Telegram no permite buscar por nombre, se necesita el user_id
        # Esta es una implementación simplificada
        await context.bot.ban_chat_member(grupo_id, estudiante_nombre)
        await context.bot.unban_chat_member(grupo_id, estudiante_nombre)
        
        await query.edit_message_text(
            f"✅ *{estudiante_nombre}* fue eliminado del grupo.",
            parse_mode='Markdown'
        )
        
        # Notificar al grupo
        await context.bot.send_message(
            grupo_id,
            f"🚫 *{estudiante_nombre}* ha sido eliminado del grupo por acumulación de strikes.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ No se pudo eliminar al estudiante. Asegúrate de que el bot tenga permisos de administrador.\n\n"
            f"Error: {str(e)}"
        )

async def monitorear_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitorea mensajes en grupos en busca de contenido inapropiado"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    # Solo en grupos registrados
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Verificar si el grupo está registrado
    grupos = db.obtener_grupos_profesor(None)
    grupo_registrado = any(chat_id == chat.id for chat_id, _ in grupos)
    
    if not grupo_registrado:
        return
    
    # No monitorear mensajes del bot
    if user.is_bot:
        return
    
    contenido = ""
    
    # Obtener contenido del mensaje
    if message.text:
        contenido = message.text
    elif message.caption:
        contenido = message.caption
    else:
        # Si es multimedia sin texto, verificar tipo
        if message.photo or message.video or message.document:
            contenido = "[Contenido multimedia]"
    
    if not contenido:
        return
    
    # Analizar con Gemini
    try:
        resultado = GeminiHandler.detectar_contenido_inapropiado(contenido)
        
        if resultado.startswith("SI"):
            # Extraer motivo
            motivo = resultado.replace("SI - ", "") if " - " in resultado else "Contenido inapropiado"
            
            # Verificar strikes actuales
            strikes_actuales = db.obtener_strikes_estudiante(user.id, chat.id)
            nuevo_strike = strikes_actuales + 1
            
            # Registrar strike
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
                # Restringir al estudiante por 24 horas
                try:
                    # Restringir permisos
                    permisos = {
                        'can_send_messages': False,
                        'can_send_media_messages': False,
                        'can_send_other_messages': False,
                        'can_add_web_page_previews': False
                    }
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
                    
                    # Notificar al profesor
                    # Buscar profesor_id del grupo
                    cursor = db.conn.cursor()
                    cursor.execute('SELECT profesor_id FROM grupos WHERE chat_id = ?', (chat.id,))
                    result = cursor.fetchone()
                    if result:
                        profesor_id = result[0]
                        await context.bot.send_message(
                            profesor_id,
                            f"🚫 *ESTUDIANTE RESTRINGIDO*\n\n"
                            f"Grupo: {chat.title}\n"
                            f"Estudiante: {user.full_name}\n"
                            f"Motivo: Acumuló 3 strikes\n"
                            f"Sanción: Sin escribir por 24 horas\n"
                            f"Fecha de liberación: {(datetime.now() + timedelta(hours=24)).strftime('%d/%m/%Y - %I:%M %p')}",
                            parse_mode='Markdown'
                        )
                
                except Exception as e:
                    await message.reply_text(
                        f"⚠️ El estudiante ha alcanzado 3 strikes pero no se pudo restringir. "
                        f"Verifica que el bot tenga permisos de administrador."
                    )
            
    except Exception as e:
        # Si falla Gemini, ignorar silenciosamente
        pass

# Método auxiliar para la base de datos
def obtener_historial_strikes_por_nombre(self, estudiante_nombre, grupo_id):
    """Obtiene el historial de strikes por nombre de estudiante"""
    self.cursor.execute(
        'SELECT motivo, fecha FROM strikes WHERE estudiante_nombre = ? AND grupo_id = ? ORDER BY fecha',
        (estudiante_nombre, grupo_id)
    )
    return self.cursor.fetchall()