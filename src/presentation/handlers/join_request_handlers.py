from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from src.application.verificacion_service import es_nombre_coincidente


async def procesar_solicitud_ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa solicitudes de ingreso al grupo mediante enlace con aprobación requerida (ChatJoinRequest)"""
    join_request = update.chat_join_request
    if not join_request:
        return

    chat = join_request.chat
    user = join_request.from_user
    db = context.bot_data['db']

    # Verificar si el grupo está registrado en el bot
    if not db.es_grupo_registrado(chat.id):
        return

    fn = user.first_name or ''
    ln = user.last_name or ''
    nombre_display = f"{fn} {ln}".strip() or f"Usuario {user.id}"
    user_tag = f"@{user.username}" if user.username else nombre_display

    # Consultar lista oficial de estudiantes del grupo
    estudiantes = db.obtener_estudiantes_grupo(chat.id)

    # Si no hay lista oficial cargada todavía para este grupo, aprobar ingreso automáticamente
    if not estudiantes:
        try:
            await join_request.approve()
            db.registrar_miembro_telegram(
                chat.id, user.id, fn, ln, user.username or ''
            )
            print(f"✅ Ingreso aprobado (sin lista oficial aún): {nombre_display} a {chat.title}")
        except TelegramError as e:
            print(f"⚠️ Error al aprobar ingreso: {e}")
        return

    # Validar identidad contra la lista oficial (verificación dual)
    es_valido = es_nombre_coincidente(fn, ln, estudiantes)

    if es_valido:
        # APROBAR SOLICITUD DE INGRESO
        try:
            await join_request.approve()

            # Registrar como miembro verificado en la base de datos
            db.registrar_miembro_telegram(
                chat.id, user.id, fn, ln, user.username or ''
            )

            # Si estaba en lista de pendientes, resolverlo
            db.resolver_pendiente(user.id, chat.id, 1)

            print(f"✅ Ingreso APROBADO: {nombre_display} en grupo {chat.title}")

            # Notificar al estudiante por mensaje privado
            try:
                await context.bot.send_message(
                    user.id,
                    f"🎉 *¡SOLICITUD DE INGRESO APROBADA!*\n\n"
                    f"Tu identidad (*{nombre_display}*) ha sido verificada en la lista oficial de estudiantes.\n\n"
                    f"📚 *Grupo:* {chat.title}\n"
                    f"¡Bienvenido al grupo académico!",
                    parse_mode='Markdown'
                )
            except Exception:
                pass  # El usuario puede no haber iniciado chat privado previo con el bot

        except TelegramError as e:
            print(f"❌ Error al aprobar a {user.id}: {e}")

    else:
        # RECHAZAR SOLICITUD DE INGRESO
        try:
            await join_request.decline()

            print(f"🚫 Ingreso RECHAZADO: {nombre_display} en grupo {chat.title}")

            # Notificar al estudiante por mensaje privado con instrucciones claras
            try:
                await context.bot.send_message(
                    user.id,
                    f"❌ *SOLICITUD DE INGRESO RECHAZADA — {chat.title}*\n\n"
                    f"Tu nombre actual en Telegram (*{nombre_display}*) no figura en la lista oficial de estudiantes de esta materia.\n\n"
                    f"⚠️ *REQUISITO OBLIGATORIO PARA PODER ENTRAR:*\n"
                    f"Debes ir a Ajustes de Telegram y modificar tu perfil colocando:\n"
                    f"👉 *PRIMER NOMBRE + PRIMER APELLIDO*\n\n"
                    f"*(Ejemplo: Nombre: 'Carlos' | Apellido: 'García')*\n\n"
                    f"Una vez actualizado tu nombre y apellido, vuelve a presionar el enlace de invitación para ingresar.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

        except TelegramError as e:
            print(f"❌ Error al rechazar a {user.id}: {e}")
