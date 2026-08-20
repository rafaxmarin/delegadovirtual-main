from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from src.presentation.keyboards import get_grupos_list_keyboard, get_grupo_detalle_keyboard
from src.presentation.auth_utils import verificar_pertenencia_grupo

async def estado_grupos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de grupos registrados por el profesor (Paso 1)"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 *ESTADO DE LOS GRUPOS*\n\n"
            "Aún no tienes grupos registrados.\n\n"
            "Agrega el bot a un grupo de Telegram para comenzar.\n"
            "Escribe /menu para volver.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    mensaje = (
        "📊 *ESTADO DE LOS GRUPOS*\n\n"
        f"Tienes *{len(grupos)}* grupo(s) registrado(s).\n"
        "Selecciona un grupo para ver la cantidad de estudiantes que lo integran:"
    )
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=get_grupos_list_keyboard(grupos)
    )

async def detalle_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la información detallada de un grupo específico (Paso 2)"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    try:
        chat_id = int(query.data.replace("detalle_grupo_", ""))
    except ValueError:
        await query.edit_message_text(
            "❌ Identificador de grupo no válido.",
            reply_markup=get_grupo_detalle_keyboard()
        )
        return

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return
        
    grupo = db.obtener_grupo(chat_id)
    nombre_grupo = grupo[1] if grupo else "Grupo"
    
    try:
        miembros = await context.bot.get_chat_member_count(chat_id)
        estudiantes = miembros - 1  # Restar el bot
        info_estudiantes = f"👥 *Estudiantes integrando el grupo:* {estudiantes}"
    except TelegramError:
        info_estudiantes = "⚠️ *Estado:* No se pudo obtener la información (el bot no está en el grupo o no tiene permisos)."
    
    mensaje = (
        f"📊 *DETALLE DEL GRUPO*\n\n"
        f"📚 *Nombre del grupo:* {nombre_grupo}\n"
        f"{info_estudiantes}\n"
        f"🆔 *ID del grupo:* `{chat_id}`"
    )
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=get_grupo_detalle_keyboard(chat_id)
    )

async def detectar_agregacion_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando el bot es agregado a un grupo y notifica al profesor (vía mensaje o my_chat_member)"""
    chat = update.effective_chat
    user = update.effective_user
    db = context.bot_data['db']
    
    if not chat or chat.type not in ['group', 'supergroup']:
        return
    
    bot_id = context.bot.id
    bot_fue_agregado = False

    if update.message and update.message.new_chat_members:
        bot_fue_agregado = any(member.id == bot_id for member in update.message.new_chat_members)
    elif update.my_chat_member:
        new_status = update.my_chat_member.new_chat_member.status
        old_status = update.my_chat_member.old_chat_member.status
        if new_status in ['member', 'administrator'] and old_status in ['left', 'kicked', 'restricted']:
            bot_fue_agregado = True
            user = update.my_chat_member.from_user
    
    # Si no fue el bot quien ingresó, salir
    if not bot_fue_agregado or not user:
        return
    
    # Si el grupo ya está registrado, evitar duplicación de mensajes
    if db.es_grupo_registrado(chat.id):
        return
    
    # Si el bot fue agregado por alguien que NO es profesor verificado, salir del grupo
    if not db.es_profesor_verificado(user.id):
        try:
            await context.bot.send_message(
                chat.id,
                "❌ Este bot es exclusivo para profesores de la UDO Monagas. "
                "Saliendo del grupo..."
            )
            await context.bot.leave_chat(chat.id)
        except Exception:
            pass
        return
    
    # Si fue agregado por un profesor verificado, enviar confirmación en privado
    keyboard = [
        [
            InlineKeyboardButton("✅ Aceptar y registrar", callback_data=f"aceptar_grupo_{chat.id}"),
            InlineKeyboardButton("❌ Rechazar y salir", callback_data=f"rechazar_grupo_{chat.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            user.id,
            f"📢 El Delegado Virtual fue agregado a un nuevo grupo:\n\n"
            f"*Nombre:* {chat.title}\n"
            f"*ID:* {chat.id}\n\n"
            "¿Qué deseas hacer?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"⚠️ No se pudo enviar mensaje privado al profesor {user.id}: {e}")

from datetime import datetime, timedelta

async def solicitar_cedula_nuevo_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita la cédula a los nuevos estudiantes que se incorporan al grupo y activa temporizador de 30 min"""
    chat = update.effective_chat
    db = context.bot_data['db']

    if not chat or chat.type not in ['group', 'supergroup']:
        return

    if not update.message or not update.message.new_chat_members:
        return

    if not db.es_grupo_registrado(chat.id):
        return

    bot_username = context.bot.username
    if not bot_username:
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception:
            bot_username = "DelegadoVirtualBot"

    bot_id = context.bot.id
    for member in update.message.new_chat_members:
        if member.id == bot_id or member.is_bot:
            continue

        nombre_display = f"{member.first_name or ''} {member.last_name or ''}".strip() or f"Usuario {member.id}"
        user_tag = f"@{member.username}" if member.username else nombre_display

        fecha_limite = datetime.now() + timedelta(minutes=30)
        fecha_limite_str = fecha_limite.strftime('%H:%M')

        # Registrar pendiente para control del temporizador de 30 min
        db.agregar_pendiente_verificacion(
            member.id, chat.id, nombre_display, fecha_limite.isoformat(), "PENDIENTE_CEDULA"
        )

        url_privado = f"https://t.me/{bot_username}?start=verificar_{chat.id}"
        keyboard = [[InlineKeyboardButton("🔐 Verificar Cédula en privado", url=url_privado)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 *¡BIENVENIDO/A AL GRUPO — {user_tag}!*\n\n"
            f"Para verificar tu inscripción en la materia de forma segura y privada, presiona el botón de abajo para enviar tu número de Cédula por chat privado.\n\n"
            f"⏰ Tienes *30 minutos* (Límite: *{fecha_limite_str}*) para verificar tu Cédula o serás expulsado del grupo.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def manejar_respuesta_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la aceptación o rechazo de un grupo"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    data = query.data
    
    if data.startswith("aceptar_grupo_"):
        chat_id = int(data.replace("aceptar_grupo_", ""))
        
        try:
            chat = await context.bot.get_chat(chat_id)
            db.registrar_grupo(chat_id, chat.title, user.id)
            
            await query.edit_message_text(
                f"✅ *Grupo registrado exitosamente*\n\n"
                f"📚 *{chat.title}* ahora está bajo tu administración.",
                parse_mode='Markdown'
            )
            
            await context.bot.send_message(
                chat_id,
                "🤖 *Delegado Virtual activado*\n\n"
                "Este grupo ahora está siendo administrado por el Delegado Virtual. "
                "Tu profesor podrá enviar anuncios, material de estudio y más a través de este canal.\n\n"
                "¡Mantengan el respeto y las normas de convivencia! 📚",
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error al registrar el grupo: {str(e)}")
    
    elif data.startswith("rechazar_grupo_"):
        chat_id = int(data.replace("rechazar_grupo_", ""))
        
        try:
            await context.bot.leave_chat(chat_id)
            await query.edit_message_text("✅ Has rechazado el grupo. El bot ha salido del mismo.")
        except Exception as e:
            await query.edit_message_text(f"❌ Error al salir del grupo: {str(e)}")

async def confirmar_desvincular_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra confirmación antes de desvincular un grupo"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']

    chat_id = int(query.data.replace("desvincular_grupo_", ""))

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return

    grupo = db.obtener_grupo(chat_id)
    nombre_grupo = grupo[1] if grupo else "el grupo"

    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, desvincular", callback_data=f"confirmar_desvincular_{chat_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data=f"detalle_grupo_{chat_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"⚠️ *¿Estás seguro de desvincular el grupo?*\n\n"
        f"📚 *{nombre_grupo}*\n\n"
        "Se eliminará el registro del grupo y el bot saldrá del mismo.\n"
        "Esta acción no se puede deshacer.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ejecutar_desvincular_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta la desvinculación del grupo: despedida, leave_chat, eliminar BD"""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']

    chat_id = int(query.data.replace("confirmar_desvincular_", ""))

    if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
        return

    grupo = db.obtener_grupo(chat_id)
    nombre_grupo = grupo[1] if grupo else "el grupo"

    try:
        # Enviar mensaje de despedida al grupo
        try:
            await context.bot.send_message(
                chat_id,
                "🤖 *El Delegado Virtual ha sido desvinculado de este grupo por el profesor.*\n\n"
                "¡Gracias por usar el servicio!",
                parse_mode='Markdown'
            )
        except Exception:
            pass  # El bot podría no tener acceso al grupo

        # El bot sale del grupo
        try:
            await context.bot.leave_chat(chat_id)
        except Exception:
            pass  # El bot podría ya no estar en el grupo

        # Eliminar registro de la base de datos
        db.eliminar_grupo(chat_id)

        await query.edit_message_text(
            f"✅ *Grupo desvinculado exitosamente*\n\n"
            f"📚 *{nombre_grupo}* ha sido eliminado de tu lista de grupos.",
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error al desvincular el grupo: {str(e)}")
