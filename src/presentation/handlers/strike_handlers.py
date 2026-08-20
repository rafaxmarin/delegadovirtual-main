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

    # 🔴 VERIFICACIÓN DE CÉDULA Y PERFIL EN TIEMPO REAL
    try:
        texto_mensaje = (message.text or message.caption or '').strip()
        import re
        match_cedula = re.match(r'^\s*(?:v-?|V-?)?\s*(\d{5,9})\s*$', texto_mensaje)

        if match_cedula:
            cedula_ingresada = match_cedula.group(1)
            estudiante = db.buscar_estudiante_por_cedula(chat.id, cedula_ingresada)

            if not estudiante:
                await message.reply_text(
                    f"❌ *CÉDULA NO REGISTRADA*\n\n"
                    f"La cédula *{cedula_ingresada}* no figura en la lista oficial de estudiantes de este grupo.\n\n"
                    f"No puedes permanecer en el grupo. Expulsando...",
                    parse_mode='Markdown'
                )
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id, only_if_banned=True)
                    db.resolver_pendiente(user.id, chat.id, 2)
                except Exception as e:
                    print(f"⚠️ Error al hacer /kick a usuario sin cédula registrada: {e}")
                return

            from src.application.verificacion_service import extraer_primer_nombre_y_apellido, comparar_perfil_telegram
            p_nomb, p_apel = extraer_primer_nombre_y_apellido(estudiante[4], estudiante[3])
            nombre_oficial = f"{p_nomb} {p_apel}".strip()

            fn_tg = user.first_name or ''
            ln_tg = user.last_name or ''
            coincide = comparar_perfil_telegram(fn_tg, ln_tg, p_nomb, p_apel)

            if coincide:
                db.resolver_pendiente(user.id, chat.id, 1)
                await message.reply_text(
                    f"🎉 *¡BIENVENIDO/A AL GRUPO!*\n\n"
                    f"👤 *{nombre_oficial}*\n\n"
                    f"Tu identidad ha sido verificada con éxito en la lista oficial.",
                    parse_mode='Markdown'
                )
                return
            else:
                fecha_limite = datetime.now() + timedelta(minutes=30)
                fecha_limite_str = fecha_limite.strftime('%H:%M')
                nombre_tg_display = f"{fn_tg} {ln_tg}".strip() or f"Usuario {user.id}"
                db.agregar_pendiente_verificacion(user.id, chat.id, nombre_tg_display, fecha_limite.isoformat(), nombre_oficial)

                user_tag = f"@{user.username}" if user.username else nombre_tg_display

                await message.reply_text(
                    f"⚠️ *AVISO DE VERIFICACIÓN — {user_tag}*\n\n"
                    f"Tu cédula (*{cedula_ingresada}*) fue verificada exitosamente a nombre de **{nombre_oficial}**.\n\n"
                    f"📌 *REQUISITO OBLIGATORIO:*\n"
                    f"Debes ir a Ajustes de Telegram y modificar tu perfil colocando:\n"
                    f"👉 *Nombre:* {p_nomb}\n"
                    f"👉 *Apellido:* {p_apel}\n\n"
                    f"⏰ Tienes *30 minutos* para realizar este cambio (Límite: *{fecha_limite_str}*).\n"
                    f"De lo contrario, serás expulsado del grupo mediante `/kick` para que puedas corregirlo e intentar nuevamente.",
                    parse_mode='Markdown'
                )
                return

        # Si no ingresó cédula, evaluar si tiene pendiente activo y ya actualizó su nombre
        pendientes = db.obtener_pendientes_activos()
        pendiente_actual = next((p for p in pendientes if p[0] == user.id and p[1] == chat.id), None)

        if pendiente_actual:
            nombre_oficial = pendiente_actual[6] if len(pendiente_actual) > 6 else ""
            fn_tg = user.first_name or ''
            ln_tg = user.last_name or ''

            if nombre_oficial == "PENDIENTE_CEDULA":
                # Aún no ingresó su cédula, recordarle si el tiempo no ha expirado
                fecha_limite_str = pendiente_actual[3]
                try:
                    fecha_limite = datetime.fromisoformat(fecha_limite_str)
                    if datetime.now() >= fecha_limite:
                        await context.bot.ban_chat_member(chat.id, user.id)
                        await context.bot.unban_chat_member(chat.id, user.id, only_if_banned=True)
                        db.resolver_pendiente(user.id, chat.id, 2)
                        nombre_display = f"{fn_tg} {ln_tg}".strip() or f"Usuario {user.id}"
                        await message.reply_text(
                            f"🚫 *{nombre_display}* ha sido expulsado del grupo (/kick) por no ingresar su "
                            f"número de Cédula dentro del plazo de 30 minutos.",
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    print(f"⚠️ Error al evaluar ultimátum de Cédula: {e}")
            else:
                estudiantes = db.obtener_estudiantes_grupo(chat.id)
                if es_nombre_coincidente(fn_tg, ln_tg, estudiantes):
                    db.resolver_pendiente(user.id, chat.id, 1)
                    p_display = nombre_oficial or f"{fn_tg} {ln_tg}".strip()
                    await message.reply_text(
                        f"🎉 *¡VERIFICACIÓN COMPLETADA!*\n\n"
                        f"👤 *{p_display}*\n\n"
                        f"Tu perfil de Telegram ha sido verificado con éxito.",
                        parse_mode='Markdown'
                    )
                else:
                    fecha_limite_str = pendiente_actual[3]
                    try:
                        fecha_limite = datetime.fromisoformat(fecha_limite_str)
                        if datetime.now() >= fecha_limite:
                            await context.bot.ban_chat_member(chat.id, user.id)
                            await context.bot.unban_chat_member(chat.id, user.id, only_if_banned=True)
                            db.resolver_pendiente(user.id, chat.id, 2)

                            msg_oficial = f" a **{nombre_oficial}**" if nombre_oficial else ""
                            nombre_display = f"{fn_tg} {ln_tg}".strip() or f"Usuario {user.id}"

                            await message.reply_text(
                                f"🚫 *{nombre_display}* ha sido expulsado del grupo (/kick) por no "
                                f"actualizar su nombre de perfil en Telegram{msg_oficial} dentro del plazo de 30 minutos.",
                                parse_mode='Markdown'
                            )
                    except Exception as e:
                        print(f"⚠️ Error al evaluar ultimátum o expulsar usuario: {e}")
    except Exception as e:
        print(f"⚠️ Error en flujo de verificación por Cédula: {e}")

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

