from telegram import Update
from telegram.ext import ContextTypes
from src.infrastructure.ai.ai_service import AIService
from src.presentation.handlers.auth_handlers import verificar_password
from src.presentation.handlers.recaudacion_handlers import procesar_recaudacion
from src.presentation.handlers.minuta_handlers import recibir_contenido_minuta
from src.presentation.handlers.alumno_handlers import recibir_datos_alumno, recibir_datos_eliminar
from src.presentation.handlers.asesoria_handlers import recibir_respuesta_asesoria
from src.presentation.handlers.material_handlers import recibir_material
from src.presentation.handlers.anuncio_handlers import recibir_anuncio
from src.presentation.handlers.reglamento_handlers import recibir_reglamento
from src.presentation.handlers.verificacion_handlers import recibir_excel_verificacion

gemini = AIService()


async def procesar_mensaje_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ÚNICO handler de mensajes privados - Redirige según el flujo activo"""
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if update.effective_chat.type != 'private':
        return
    if not message:
        return
    
    # 🔴 Si está esperando la contraseña, procesarla sin importar que no esté verificado aún
    if context.user_data.get('esperando_password'):
        await verificar_password(update, context)
        return
    
    # 🔴 Si está un estudiante respondiendo su Cédula por privado
    if context.user_data.get('esperando_cedula_grupo'):
        await procesar_cedula_privada(update, context)
        return

    # Si no está verificado como profesor, atender de forma inteligente si es estudiante
    if not db.es_profesor_verificado(user.id):
        import re
        texto = message.text.strip() if message.text else ""
        if re.match(r'^\s*\d{5,9}\s*$', texto):
            # Si envió únicamente un número (Cédula) pero no tenía el flag guardado aún, intentar procesar
            pendientes = db.obtener_pendientes_activos()
            pendiente_usuario = next((p for p in pendientes if p[0] == user.id), None)
            if pendiente_usuario:
                context.user_data['esperando_cedula_grupo'] = pendiente_usuario[1]
                await procesar_cedula_privada(update, context)
                return
            else:
                await message.reply_text(
                    "👋 *Hola.*\n\n"
                    "Para verificar tu acceso a la materia con tu Cédula, por favor ingresa primero al grupo mediante el enlace de invitación de tu profesor o presiona el botón *🔐 Verificar Cédula en privado* en el grupo.",
                    parse_mode='Markdown'
                )
                return
        else:
            await message.reply_text(
                "👋 *Bienvenido al Delegado Virtual — UDO Monagas*\n\n"
                "🎓 *Estudiantes:* Para ingresar a tu materia, utiliza el enlace de invitación proporcionado por tu profesor o escribe tu número de *Cédula*.\n\n"
                "👨‍🏫 *Profesores:* Escribe `/start` para ingresar tu contraseña de acceso.",
                parse_mode='Markdown'
            )
            return
    
    # Flujo de verificación de miembros (recibe Excel como documento)
    if context.user_data.get('esperando_excel_verificacion') and message.document:
        await recibir_excel_verificacion(update, context)
        return

    texto = message.text.strip() if message.text else ""
    if texto.lower() in ['cancelar', 'cancel', 'salir']:
        context.user_data.clear()
        from src.presentation.handlers.menu_handlers import menu
        await menu(update, context)
        return

    # Verificar flujos activos en orden
    if context.user_data.get('creando_recaudacion'):
        await procesar_recaudacion(update, context)
        return
    
    if context.user_data.get('esperando_anuncio'):
        await recibir_anuncio(update, context)
        return

    if context.user_data.get('esperando_minuta'):
        await recibir_contenido_minuta(update, context)
        return

    if context.user_data.get('esperando_material'):
        await recibir_material(update, context)
        return

    if context.user_data.get('esperando_reglamento'):
        await recibir_reglamento(update, context)
        return
    
    if context.user_data.get('agregando_alumno'):
        await recibir_datos_alumno(update, context)
        return
    
    if context.user_data.get('esperando_datos_eliminar'):
        await recibir_datos_eliminar(update, context)
        return
    
    if context.user_data.get('respondiendo_asesoria'):
        await recibir_respuesta_asesoria(update, context)
        return
    
    if not texto:
        return
    
    # Conversación natural / Intención con IA
    try:
        intencion = gemini.interpretar_intencion(texto)
        funciones = {'1': 'Estado de grupos', '2': 'Recaudación', '3': 'Emitir anuncio',
                     '4': 'Redactar minuta', '5': 'Compartir material', '6': 'Buzón de asesoría'}
        if intencion in funciones:
            await message.reply_text(f"🤔 Quieres: *{funciones[intencion]}*\nUsa /menu.", parse_mode='Markdown')
        else:
            respuesta = gemini.responder_conversacion(texto)
            await message.reply_text(respuesta)
    except Exception:
        await message.reply_text("Usa /menu para ver las opciones.")

async def procesar_cedula_privada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el número de Cédula ingresado por un estudiante en chat privado"""
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    chat_id = context.user_data.get('esperando_cedula_grupo')

    if not message or not message.text or not chat_id:
        return

    import re
    cedula_ingresada = re.sub(r'\D', '', message.text)
    if not cedula_ingresada:
        await message.reply_text("⚠️ Por favor ingresa únicamente los números de tu Cédula (ej: `12345678`).", parse_mode='Markdown')
        return

    try:
        chat = await context.bot.get_chat(chat_id)
        nombre_grupo = chat.title or "el grupo"
    except Exception:
        nombre_grupo = "el grupo"

    estudiante = db.buscar_estudiante_por_cedula(chat_id, cedula_ingresada)

    if not estudiante:
        try:
            await context.bot.decline_chat_join_request(chat_id, user.id)
        except Exception:
            pass

        await message.reply_text(
            f"❌ *CÉDULA NO REGISTRADA*\n\n"
            f"La cédula *{cedula_ingresada}* no figura en la lista oficial de estudiantes para *{nombre_grupo}*.\n\n"
            f"Tu solicitud de ingreso ha sido rechazada.",
            parse_mode='Markdown'
        )
        context.user_data.pop('esperando_cedula_grupo', None)
        return

    from src.application.verificacion_service import extraer_primer_nombre_y_apellido, comparar_perfil_telegram
    p_nomb, p_apel = extraer_primer_nombre_y_apellido(estudiante[4], estudiante[3])
    nombre_oficial = f"{p_nomb} {p_apel}".strip()

    fn_tg = user.first_name or ''
    ln_tg = user.last_name or ''
    coincide = comparar_perfil_telegram(fn_tg, ln_tg, p_nomb, p_apel)

    if coincide:
        db.resolver_pendiente(user.id, chat_id, 1)
        
        # Aprobar solicitud de ingreso si existe
        try:
            await context.bot.approve_chat_join_request(chat_id, user.id)
        except Exception:
            pass

        await message.reply_text(
            f"🎉 *¡VERIFICACIÓN COMPLETADA!*\n\n"
            f"👤 *{nombre_oficial}*\n\n"
            f"Tu identidad ha sido verificada con éxito. ¡Tu solicitud de ingreso a *{nombre_grupo}* ha sido APROBADA!",
            parse_mode='Markdown'
        )
        try:
            await context.bot.send_message(
                chat_id,
                f"🎉 *¡BIENVENIDO/A AL GRUPO!*\n\n"
                f"👤 *{nombre_oficial}*\n\n"
                f"Tu identidad ha sido verificada con éxito en la lista oficial.",
                parse_mode='Markdown'
            )
        except Exception:
            pass
    else:
        # Rechazar temporalmente la solicitud actual para instar al cambio de nombre
        try:
            await context.bot.decline_chat_join_request(chat_id, user.id)
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ *REQUISITO OBLIGATORIO — {nombre_grupo}*\n\n"
            f"Tu cédula (*{cedula_ingresada}*) pertenece a **{nombre_oficial}** en la lista oficial.\n\n"
            f"📌 *PARA QUE TU INGRESO SEA APROBADO:*\n"
            f"Debes ir a Ajustes de Telegram y modificar tu perfil colocando:\n"
            f"👉 *Nombre:* {p_nomb}\n"
            f"👉 *Apellido:* {p_apel}\n\n"
            f"Una vez actualizado tu perfil en Telegram, vuelve a presionar el enlace de invitación del grupo para ingresar automáticamente.",
            parse_mode='Markdown'
        )

    context.user_data.pop('esperando_cedula_grupo', None)
