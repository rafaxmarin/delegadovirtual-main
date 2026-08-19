from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from src.infrastructure.ai.ai_service import AIService
from src.presentation.auth_utils import verificar_pertenencia_grupo
from src.application.verificacion_service import es_nombre_coincidente

gemini = AIService()

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

    if not await verificar_pertenencia_grupo(grupo_id, query.from_user.id, db, query):
        return
    
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

PALABRAS_OFENSIVAS = [
    'mierda', 'puta', 'puto', 'pendejo', 'pendeja', 'coño', 'maldito', 'maldita',
    'mamaguevo', 'mamagüevo', 'mamaguebo', 'marico', 'marica', 'idiota', 'estúpido',
    'estupido', 'estúpida', 'estupida', 'imbécil', 'imbecil', 'perra', 'bobo',
    'huevón', 'huevon', 'guevón', 'guevon', 'coñodemadre', 'verga'
]

async def monitorear_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitorea mensajes en grupos e impone strikes si hay lenguaje o contenido inapropiado"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if chat.type not in ['group', 'supergroup']:
        return
    
    if not message:
        return
    
    if not db.es_grupo_registrado(chat.id):
        return
    
    if user.is_bot:
        return

    # Excluir de strikes al profesor del grupo o profesores verificados
    profesor_id = db.obtener_profesor_de_grupo(chat.id)
    if user.id == profesor_id or db.es_profesor_verificado(user.id):
        return

    # Registro pasivo de miembros del grupo para verificación
    try:
        db.registrar_miembro_telegram(
            chat.id, user.id,
            user.first_name or '', user.last_name or '',
            user.username or ''
        )
    except Exception:
        pass  # No interrumpir el flujo si falla el registro

    # 🔴 VERIFICACIÓN EN TIEMPO REAL AL ESCRIBIR
    try:
        estudiantes = db.obtener_estudiantes_grupo(chat.id)
        if estudiantes:
            fn = user.first_name or ''
            ln = user.last_name or ''
            es_valido = es_nombre_coincidente(fn, ln, estudiantes)
            nombre_display = f"{fn} {ln}".strip() or f"Usuario {user.id}"
            user_tag = f"@{user.username}" if user.username else nombre_display

            if es_valido:
                # Si estaba en pendientes, marcar como verificado
                db.resolver_pendiente(user.id, chat.id, 1)
            else:
                # Buscar si ya está en pendientes de este grupo
                pendientes = db.obtener_pendientes_activos()
                pendiente_actual = next((p for p in pendientes if p[0] == user.id and p[1] == chat.id), None)

                if not pendiente_actual:
                    # Primera vez detectado no verificado: darle 12 horas y notificar
                    fecha_limite = datetime.now() + timedelta(hours=12)
                    fecha_limite_str = fecha_limite.strftime('%d/%m/%Y %H:%M')
                    db.agregar_pendiente_verificacion(user.id, chat.id, nombre_display, fecha_limite.isoformat())

                    # Notificar al estudiante en el grupo
                    await message.reply_text(
                        f"⚠️ *AVISO DE VERIFICACIÓN — {user_tag}*\n\n"
                        f"Tu nombre en Telegram (*{nombre_display}*) NO coincide con la lista oficial de estudiantes de este grupo.\n\n"
                        f"📌 *Por favor modifica tu nombre y apellido en Telegram a:*\n"
                        f"*PRIMER NOMBRE + PRIMER APELLIDO*\n\n"
                        f"⏰ Tienes *12 horas* para realizar el cambio (Límite: *{fecha_limite_str}*). "
                        f"De lo contrario, serás expulsado automáticamente del grupo.",
                        parse_mode='Markdown'
                    )

                    # Enviar reporte inmediato al profesor
                    if profesor_id:
                        try:
                            chat_title = chat.title or "el grupo"
                            await context.bot.send_message(
                                profesor_id,
                                f"🚨 *REPORTE EN VIVO: MIEMBRO NO VERIFICADO*\n\n"
                                f"📚 *Grupo:* {chat_title}\n"
                                f"👤 *Usuario:* {nombre_display} ({user_tag})\n"
                                f"🆔 *ID:* `{user.id}`\n\n"
                                f"⚠️ Acaba de escribir en el grupo pero NO aparece en la lista oficial de estudiantes.\n"
                                f"⏰ Notificado en el grupo con ultimátum de 12 horas (Límite: {fecha_limite_str}).",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            print(f"⚠️ Error al notificar al profesor: {e}")

                else:
                    # Ya estaba en pendientes: verificar si transcurrieron las 12 horas
                    fecha_limite_str = pendiente_actual[3]
                    try:
                        fecha_limite = datetime.fromisoformat(fecha_limite_str)
                        if datetime.now() >= fecha_limite:
                            # 12 horas cumplidas sin cambiar nombre -> expulsar
                            await context.bot.ban_chat_member(chat.id, user.id)
                            await context.bot.unban_chat_member(chat.id, user.id, only_if_banned=True)
                            db.resolver_pendiente(user.id, chat.id, 2)

                            await message.reply_text(
                                f"🚫 *{nombre_display}* ha sido expulsado del grupo por no "
                                f"actualizar su nombre según la lista oficial dentro del plazo de 12 horas.",
                                parse_mode='Markdown'
                            )
                            if profesor_id:
                                await context.bot.send_message(
                                    profesor_id,
                                    f"🚫 *REPORTE DE EXPULSIÓN AUTOMÁTICA*\n\n"
                                    f"📚 *Grupo:* {chat.title}\n"
                                    f"👤 *Usuario:* {nombre_display} ({user_tag})\n"
                                    f"⏰ Expulsado automáticamente tras cumplir 12 horas sin verificar su nombre.",
                                    parse_mode='Markdown'
                                )
                    except Exception as e:
                        print(f"⚠️ Error al evaluar ultimátum o expulsar usuario: {e}")
    except Exception as e:
        print(f"⚠️ Error en flujo de verificación en tiempo real: {e}")

    contenido = ""
    if message.text:
        contenido = message.text
    elif message.caption:
        contenido = message.caption
    elif message.photo or message.video or message.document:
        contenido = "[Contenido multimedia]"
    
    if not contenido:
        return

    es_inapropiado = False
    motivo = "Uso de lenguaje inapropiado"

    # 1. Verificación rápida local de groserías conocidas
    import re
    texto_clean = re.sub(r'[^\w\s]', '', contenido.lower())
    palabras = texto_clean.split()
    for p in palabras:
        if p in PALABRAS_OFENSIVAS:
            es_inapropiado = True
            motivo = f"Lenguaje inapropiado ('{p}')"
            break

    # 2. Verificación por IA si la revisión local no la detectó
    if not es_inapropiado and len(contenido.strip()) > 2:
        try:
            resultado = gemini.detectar_contenido_inapropiado(contenido)
            res_clean = re.sub(r'[ÁÁáàâä]', 'A', re.sub(r'[ÉÉéèêë]', 'E', re.sub(r'[ÍÍíìîï]', 'I', re.sub(r'[ÓÓóòôö]', 'O', re.sub(r'[ÚÚúùûü]', 'U', resultado.upper())))))
            
            if res_clean.startswith("SI") or "SI -" in res_clean or "SI:" in res_clean or "INAPROPIADO" in res_clean:
                es_inapropiado = True
                if " - " in resultado:
                    motivo = resultado.split(" - ", 1)[1].strip()
                elif ":" in resultado:
                    motivo = resultado.split(":", 1)[1].strip()
                else:
                    motivo = "Contenido inapropiado detectado por IA"
        except Exception as e:
            print(f"⚠️ Error en análisis IA para strikes: {e}")

    if es_inapropiado:
        try:
            strikes_actuales = db.obtener_strikes_estudiante(user.id, chat.id)
            nuevo_strike = strikes_actuales + 1
            
            db.agregar_strike(user.id, user.full_name or f"Estudiante {user.id}", chat.id, motivo)
            print(f"⚡ Strike registrado a {user.full_name} (ID: {user.id}) en grupo {chat.id}. Total strikes: {nuevo_strike}")
            
            if nuevo_strike == 1:
                await message.reply_text(
                    f"⚠️ *STRIKE 1/3 — {user.full_name}*\n"
                    f"📝 *Motivo:* {motivo}\n\n"
                    "Por favor, mantén el respeto y el lenguaje adecuado en el grupo.",
                    parse_mode='Markdown',
                    reply_to_message_id=message.message_id
                )
            elif nuevo_strike == 2:
                await message.reply_text(
                    f"⚠️ *STRIKE 2/3 — {user.full_name}*\n"
                    f"📝 *Motivo:* {motivo}\n\n"
                    "⚠️ *¡Último aviso!* Un strike más y serás silenciado por 24 horas.",
                    parse_mode='Markdown',
                    reply_to_message_id=message.message_id
                )
            elif nuevo_strike >= 3:
                try:
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
                        f"🚫 *RESTRICCIÓN ALCANZADA (3/3 STRIKES) — {user.full_name}*\n\n"
                        f"Has sido silenciado en este grupo durante 24 horas por faltas consecutivas al reglamento.",
                        parse_mode='Markdown',
                        reply_to_message_id=message.message_id
                    )
                except Exception as e:
                    print(f"⚠️ No se pudo silenciar al estudiante en Telegram: {e}")
                    await message.reply_text(
                        f"⚠️ *STRIKE 3/3 — {user.full_name}*\n"
                        f"El estudiante alcanzó 3 strikes pero el bot no posee permisos de administrador para silenciarlo.",
                        reply_to_message_id=message.message_id
                    )
        except Exception as e:
            print(f"❌ Error al procesar strike: {e}")

