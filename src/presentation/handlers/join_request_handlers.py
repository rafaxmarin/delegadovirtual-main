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
        # APROBAR SOLICITUD DE INGRESO DIRECTAMENTE
        try:
            await join_request.approve()

            db.registrar_miembro_telegram(
                chat.id, user.id, fn, ln, user.username or ''
            )
            db.resolver_pendiente(user.id, chat.id, 1)

            print(f"✅ Ingreso APROBADO: {nombre_display} en grupo {chat.title}")

            # Mensaje de bienvenida en el grupo
            try:
                await context.bot.send_message(
                    chat.id,
                    f"🎉 *¡BIENVENIDO/A AL GRUPO!*\n\n"
                    f"👤 *{nombre_display}*\n\n"
                    f"Tu identidad ha sido verificada con éxito en la lista oficial.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

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
                pass

        except TelegramError as e:
            print(f"❌ Error al aprobar a {user.id}: {e}")

    else:
        # Si el nombre no coincide directamente, solicitar Cédula por privado para pre-validación
        try:
            context.user_data['esperando_cedula_grupo'] = chat.id

            await context.bot.send_message(
                user.id,
                f"🔐 *PRE-VERIFICACIÓN DE INGRESO — {chat.title}*\n\n"
                f"Tu nombre actual en Telegram (*{nombre_display}*) aún no está verificado en la lista oficial.\n\n"
                f"Para aprobar tu ingreso al grupo de forma segura, por favor responde a este mensaje enviando tu número de *Cédula* (solo números, ej: `12345678`):",
                parse_mode='Markdown'
            )
            print(f"📩 Solicitud de Cédula enviada por DM a {nombre_display} para pre-ingreso a {chat.title}")
        except Exception:
            # Si el usuario no tiene chat previo iniciado con el bot, notificar y rechazar con instrucción
            try:
                await join_request.decline()
                print(f"🚫 Ingreso RECHAZADO (sin chat previo): {nombre_display} en grupo {chat.title}")
            except Exception as e:
                print(f"❌ Error al rechazar a {user.id}: {e}")
