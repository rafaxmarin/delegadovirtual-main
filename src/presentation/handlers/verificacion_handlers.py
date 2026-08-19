import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime, timedelta
from src.application.verificacion_service import leer_excel_estudiantes, verificar_miembros
from src.presentation.auth_utils import verificar_pertenencia_grupo


async def verificar_miembros_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de verificación de miembros — pide el Excel"""
    query = update.callback_query
    await query.answer()

    context.user_data['esperando_excel_verificacion'] = True

    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✅ *VERIFICACIÓN DE MIEMBROS*\n\n"
        "Envía el archivo Excel (.xlsx) con la lista de estudiantes.\n\n"
        "El archivo debe contener las columnas:\n"
        "• *Cédula*\n"
        "• *Apellidos*\n"
        "• *Nombres*\n"
        "• *Correo*\n\n"
        "📎 Envía el archivo como documento adjunto.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def recibir_excel_verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el archivo Excel, lo parsea y pide seleccionar grupo"""
    message = update.message
    user = update.effective_user
    db = context.bot_data['db']

    context.user_data['esperando_excel_verificacion'] = False

    document = message.document
    if not document:
        await message.reply_text("❌ No se detectó un archivo. Por favor envía un archivo Excel (.xlsx).")
        context.user_data['esperando_excel_verificacion'] = True
        return

    file_name = document.file_name or ''
    if not file_name.lower().endswith(('.xlsx', '.xls')):
        await message.reply_text(
            "❌ El archivo debe ser un Excel (.xlsx).\n"
            "Por favor envía el archivo correcto."
        )
        context.user_data['esperando_excel_verificacion'] = True
        return

    # Descargar el archivo
    try:
        file = await context.bot.get_file(document.file_id)
        temp_path = os.path.join(tempfile.gettempdir(), f"verificacion_{user.id}.xlsx")
        await file.download_to_drive(temp_path)
    except Exception as e:
        await message.reply_text(f"❌ Error al descargar el archivo: {str(e)}")
        return

    # Parsear el Excel
    try:
        estudiantes = leer_excel_estudiantes(temp_path)
    except ValueError as e:
        await message.reply_text(f"❌ Error en el formato del Excel:\n{str(e)}")
        return
    except Exception as e:
        await message.reply_text(f"❌ Error al leer el archivo Excel:\n{str(e)}")
        return
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

    if not estudiantes:
        await message.reply_text("❌ El archivo Excel está vacío o no contiene datos válidos.")
        return

    # Guardar datos temporalmente
    context.user_data['datos_excel_verificacion'] = estudiantes

    # Mostrar grupos para seleccionar
    grupos = db.obtener_grupos_profesor(user.id)

    if not grupos:
        await message.reply_text("❌ No tienes grupos registrados.")
        context.user_data.pop('datos_excel_verificacion', None)
        return

    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(
            f"📚 {nombre}",
            callback_data=f"cargar_verificacion_{chat_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"📋 Se encontraron *{len(estudiantes)}* estudiantes en el Excel.\n\n"
        "¿A qué grupo deseas asociar esta lista y verificar?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def seleccionar_grupo_verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda estudiantes en BD, ejecuta verificación y muestra reporte"""
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.replace("cargar_verificacion_", ""))
    user = query.from_user
    db = context.bot_data['db']

    estudiantes = context.user_data.get('datos_excel_verificacion')
    if not estudiantes:
        await query.edit_message_text("❌ No hay datos del Excel. Inicia el proceso nuevamente.")
        return

    if not await verificar_pertenencia_grupo(chat_id, user.id, db, query):
        return

    # Obtener nombre del grupo
    try:
        chat = await context.bot.get_chat(chat_id)
        nombre_grupo = chat.title
    except Exception:
        nombre_grupo = "el grupo"

    # Reemplazar estudiantes anteriores del grupo
    db.eliminar_estudiantes_grupo(chat_id)

    # Guardar nuevos estudiantes
    for est in estudiantes:
        db.guardar_estudiante_grupo(
            chat_id,
            est['cedula'],
            est['apellidos'],
            est['nombres'],
            est['correo']
        )

    # Obtener miembros de Telegram detectados en este grupo
    miembros_telegram = db.obtener_miembros_telegram(chat_id)

    if not miembros_telegram:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ Se cargaron *{len(estudiantes)}* estudiantes para *{nombre_grupo}*.\n\n"
            "⚠️ Aún no se han detectado miembros en el grupo. "
            "Los miembros se registran automáticamente cuando escriben en el grupo.\n\n"
            "Pide a los estudiantes que envíen un mensaje en el grupo y luego vuelve a verificar.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        context.user_data.pop('datos_excel_verificacion', None)
        return

    # Ejecutar verificación
    verificados, no_registrados = verificar_miembros(estudiantes, miembros_telegram)

    # Guardar para paso de notificación
    context.user_data['no_registrados_verificacion'] = no_registrados
    context.user_data['grupo_verificacion'] = chat_id
    context.user_data.pop('datos_excel_verificacion', None)

    if not no_registrados:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ *VERIFICACIÓN COMPLETA — {nombre_grupo}*\n\n"
            f"📋 Estudiantes en lista: {len(estudiantes)}\n"
            f"👥 Miembros detectados: {len(miembros_telegram)}\n\n"
            "🎉 *Todos los miembros detectados coinciden con la lista!*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return

    # Construir reporte (solo NO registrados)
    mensaje = (
        f"📋 *VERIFICACIÓN — {nombre_grupo}*\n\n"
        f"📄 Estudiantes en lista: {len(estudiantes)}\n"
        f"👥 Miembros detectados: {len(miembros_telegram)}\n"
        f"✅ Verificados: {len(verificados)}\n"
        f"❌ No registrados: {len(no_registrados)}\n\n"
        f"❌ *NO REGISTRADOS EN LA LISTA:*\n"
    )

    for i, miembro in enumerate(no_registrados, 1):
        user_id_m, first_name, last_name, username = miembro
        nombre_display = f"{first_name or ''} {last_name or ''}".strip()
        username_display = f" (@{username})" if username else ""
        mensaje += f"  {i}. {nombre_display}{username_display}\n"

    keyboard = [
        [InlineKeyboardButton(
            "📢 Notificar al grupo (12h para cambiar nombre)",
            callback_data=f"notificar_verificacion_{chat_id}"
        )],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def notificar_grupo_verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía ultimátum al grupo y guarda pendientes de verificación"""
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.replace("notificar_verificacion_", ""))
    db = context.bot_data['db']

    no_registrados = context.user_data.get('no_registrados_verificacion', [])

    if not no_registrados:
        await query.edit_message_text("❌ No hay miembros para notificar.")
        return

    # Obtener nombre del grupo
    try:
        chat = await context.bot.get_chat(chat_id)
        nombre_grupo = chat.title
    except Exception:
        nombre_grupo = "el grupo"

    # Construir mensaje de notificación con menciones
    fecha_limite = datetime.now() + timedelta(hours=12)
    fecha_limite_str = fecha_limite.strftime('%d/%m/%Y %H:%M')

    lista_mencionados = ""
    for miembro in no_registrados:
        user_id_m, first_name, last_name, username = miembro
        nombre_display = f"{first_name or ''} {last_name or ''}".strip() or f"Usuario {user_id_m}"
        if username:
            lista_mencionados += f"  • @{username}\n"
        else:
            lista_mencionados += f"  • {nombre_display}\n"

    mensaje_grupo = (
        "⚠️ *AVISO IMPORTANTE — VERIFICACIÓN DE MIEMBROS*\n\n"
        "Los siguientes miembros *NO aparecen* en la lista oficial del grupo:\n\n"
        f"{lista_mencionados}\n"
        "📌 *Deben modificar su nombre en Telegram a:*\n"
        "*PRIMER NOMBRE + PRIMER APELLIDO*\n\n"
        f"⏰ *Tienen hasta las {fecha_limite_str} (12 horas)* para hacerlo.\n"
        "De lo contrario, serán *expulsados automáticamente* del grupo."
    )

    try:
        await context.bot.send_message(
            chat_id,
            mensaje_grupo,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error al enviar la notificación al grupo: {str(e)}"
        )
        return

    # Guardar pendientes en la base de datos
    fecha_limite_iso = fecha_limite.isoformat()
    for miembro in no_registrados:
        user_id_m, first_name, last_name, username = miembro
        nombre_display = f"{first_name or ''} {last_name or ''}".strip()
        db.agregar_pendiente_verificacion(
            user_id_m, chat_id, nombre_display, fecha_limite_iso
        )

    # Limpiar contexto
    context.user_data.pop('no_registrados_verificacion', None)
    context.user_data.pop('grupo_verificacion', None)

    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ *Notificación enviada a {nombre_grupo}*\n\n"
        f"📢 Se notificó a {len(no_registrados)} miembro(s).\n"
        f"⏰ Fecha límite: {fecha_limite_str}\n\n"
        "El bot verificará automáticamente cada 30 minutos. "
        "Si no cambian su nombre antes del plazo, serán expulsados.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def verificar_pendientes_job(context: ContextTypes.DEFAULT_TYPE):
    """Job periódico que revisa pendientes de verificación y expulsa si es necesario"""
    db = context.bot_data['db']

    pendientes = db.obtener_pendientes_activos()
    if not pendientes:
        return

    ahora = datetime.now()

    for pendiente in pendientes:
        p_user_id, p_chat_id, nombre_telegram, fecha_limite_str, notificado, resuelto = pendiente

        try:
            fecha_limite = datetime.fromisoformat(fecha_limite_str)
        except (ValueError, TypeError):
            continue

        # Obtener datos actuales del miembro desde Telegram
        try:
            member = await context.bot.get_chat_member(p_chat_id, p_user_id)
            current_first = member.user.first_name or ''
            current_last = member.user.last_name or ''
            current_username = member.user.username or ''
        except TelegramError:
            # El miembro ya no está en el grupo
            db.resolver_pendiente(p_user_id, p_chat_id, 2)
            continue

        # Actualizar datos del miembro en la tabla de Telegram
        db.registrar_miembro_telegram(
            p_chat_id, p_user_id,
            current_first, current_last, current_username
        )

        # Re-verificar contra la lista de estudiantes
        estudiantes = db.obtener_estudiantes_grupo(p_chat_id)
        miembro_actual = [(p_user_id, current_first, current_last, current_username)]
        verificados, no_registrados = verificar_miembros(estudiantes, miembro_actual)

        if verificados:
            # Ahora coincide — marcar como verificado
            db.resolver_pendiente(p_user_id, p_chat_id, 1)
            print(f"✅ Verificación resuelta: {current_first} {current_last} en grupo {p_chat_id}")
            continue

        # Sigue sin coincidir — verificar si expiró el plazo
        if ahora >= fecha_limite:
            # Tiempo agotado — expulsar
            try:
                await context.bot.ban_chat_member(p_chat_id, p_user_id)
                # Desbanear para permitir re-ingreso futuro
                await context.bot.unban_chat_member(p_chat_id, p_user_id, only_if_banned=True)

                db.resolver_pendiente(p_user_id, p_chat_id, 2)

                try:
                    chat = await context.bot.get_chat(p_chat_id)
                    nombre_grupo = chat.title
                except Exception:
                    nombre_grupo = "el grupo"

                nombre_display = f"{current_first} {current_last}".strip()

                # Notificar al grupo
                try:
                    await context.bot.send_message(
                        p_chat_id,
                        f"🚫 *{nombre_display}* ha sido expulsado del grupo por no "
                        f"actualizar su nombre según la lista oficial.",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

                print(f"🚫 Kick ejecutado: {nombre_display} de grupo {p_chat_id}")

            except TelegramError as e:
                print(f"❌ Error al expulsar a {p_user_id} de {p_chat_id}: {e}")
