from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from telegram.error import TelegramError # type: ignore
import asyncio

async def agregar_alumno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para agregar un alumno"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['agregando_alumno'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ *AGREGAR ALUMNO*\n\n"
        "Proporciona el número de teléfono o el @nombredeusuario "
        "del estudiante que deseas agregar.\n\n"
        "Ejemplo: +584121234567 o @carlosmartinez",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
async def recibir_datos_alumno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('agregando_alumno'):
        return

async def recibir_datos_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('esperando_datos_eliminar'):
        return
    
    datos_alumno = update.message.text.strip()
    user = update.effective_user
    db = context.bot_data['db']
    
    # Guardar datos
    context.user_data['datos_alumno'] = datos_alumno
    context.user_data['agregando_alumno'] = False
    
    # Mostrar grupos disponibles
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await update.message.reply_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"invitar_alumno_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📋 ¿A qué grupo deseas agregar a {datos_alumno}?",
        reply_markup=reply_markup
    )

async def invitar_alumno_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera invitación y la envía al alumno"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("invitar_alumno_", ""))
    datos_alumno = context.user_data.get('datos_alumno')
    
    if not datos_alumno:
        await query.edit_message_text("❌ No hay datos del alumno.")
        return
    
    try:
        # Obtener información del grupo
        chat = await context.bot.get_chat(chat_id)
        
        # Generar enlace de invitación temporal
        invite_link = await context.bot.create_chat_invite_link(
            chat_id,
            expire_date=None,  # Sin expiración
            member_limit=1     # Solo para una persona
        )
        
        # Intentar enviar invitación al alumno
        mensaje_invitacion = (
            f"📚 *INVITACIÓN ACADÉMICA*\n\n"
            f"Has sido invitado a unirte al grupo:\n"
            f"*{chat.title}*\n\n"
            f"Este es un grupo académico de la Universidad de Oriente, "
            f"Núcleo Monagas.\n\n"
            f"🔗 *Enlace de invitación:* {invite_link.invite_link}\n\n"
            f"¡Te esperamos!"
        )
        
        # Determinar si es username o teléfono
        if datos_alumno.startswith('@'):
            # Es username, enviar por chat privado
            try:
                await context.bot.send_message(
                    datos_alumno,
                    mensaje_invitacion,
                    parse_mode='Markdown'
                )
                await query.edit_message_text(
                    f"✅ Invitación enviada a {datos_alumno} "
                    f"para unirse a {chat.title}."
                )
            except TelegramError:
                await query.edit_message_text(
                    f"❌ No se pudo enviar la invitación. "
                    f"Verifica que el usuario {datos_alumno} exista "
                    f"y haya iniciado el bot previamente.\n\n"
                    f"🔗 Enlace de invitación: {invite_link.invite_link}"
                )
        else:
            # Es número de teléfono, enviar enlace directamente
            await query.edit_message_text(
                f"✅ Invitación generada para {datos_alumno}.\n\n"
                f"Comparte este enlace al estudiante:\n"
                f"🔗 {invite_link.invite_link}\n\n"
                f"Grupo: {chat.title}"
            )
        
        # Limpiar contexto
        context.user_data.pop('datos_alumno', None)
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error al generar la invitación. "
            f"Verifica que el bot tenga permisos de administrador en el grupo.\n\n"
            f"Error: {str(e)}"
        )

async def eliminar_alumno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para eliminar un alumno"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text("❌ No tienes grupos registrados.")
        return
    
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"listar_estudiantes_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="volver_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➖ *ELIMINAR ALUMNO*\n\n"
        "Selecciona el grupo de donde deseas eliminar a un estudiante:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def listar_estudiantes_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista los estudiantes de un grupo para seleccionar a quién eliminar"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("listar_estudiantes_", ""))
    
    await query.edit_message_text("⏳ Obteniendo lista de estudiantes...")
    
    try:
        # Obtener chat
        chat = await context.bot.get_chat(chat_id)
        
        # Obtener lista de administradores y miembros
        # Nota: get_chat_administrators obtiene admins, no todos los miembros
        # Para obtener todos los miembros se necesita que el usuario haya interactuado
        
        mensaje = f"📚 *{chat.title}* - Lista de miembros:\n\n"
        mensaje += "Para eliminar a un estudiante, necesitas proporcionar "
        mensaje += "su @username o número de teléfono.\n\n"
        
        context.user_data['eliminando_de_grupo'] = chat_id
        context.user_data['esperando_datos_eliminar'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data="menu_eliminar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            mensaje + "Envía el @username o número de teléfono del estudiante a eliminar:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error al obtener la lista de estudiantes: {str(e)}"
        )

async def recibir_datos_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe los datos del estudiante a eliminar y confirma"""
    if not context.user_data.get('esperando_datos_eliminar'):
        return
    
    datos_estudiante = update.message.text.strip()
    chat_id = context.user_data.get('eliminando_de_grupo')
    
    if not chat_id:
        return
    
    context.user_data['datos_eliminar'] = datos_estudiante
    context.user_data['esperando_datos_eliminar'] = False
    
    # Obtener nombre del grupo
    try:
        chat = await context.bot.get_chat(chat_id)
        nombre_grupo = chat.title
    except:
        nombre_grupo = "el grupo"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"confirmar_eliminar_alumno_{chat_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🚫 ¿Deseas eliminar a *{datos_estudiante}* de *{nombre_grupo}*?\n\n"
        "Esta acción no se puede deshacer.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def confirmar_eliminar_alumno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina al estudiante del grupo"""
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.replace("confirmar_eliminar_alumno_", ""))
    datos_estudiante = context.user_data.get('datos_eliminar')
    
    if not datos_estudiante:
        await query.edit_message_text("❌ No hay datos del estudiante.")
        return
    
    try:
        # Intentar obtener el user_id del estudiante
        user_id = None
        
        if datos_estudiante.startswith('@'):
            # Buscar por username (requiere que el bot haya visto al usuario)
            try:
                # Esto es una limitación de la API de Telegram
                # Se necesita que el usuario haya interactuado con el bot
                pass
            except:
                pass
        
        # Intentar banear y desbanear (expulsar)
        if user_id:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
        else:
            # Si no tenemos user_id, informar al profesor
            await query.edit_message_text(
                f"⚠️ No se pudo identificar automáticamente a {datos_estudiante}.\n\n"
                f"Para eliminar manualmente, ve al grupo y elimina al usuario.\n"
                f"O asegúrate de que el usuario haya enviado al menos un mensaje "
                f"en el grupo para que el bot pueda identificarlo."
            )
            return
        
        # Obtener nombre del grupo
        chat = await context.bot.get_chat(chat_id)
        
        await query.edit_message_text(
            f"✅ *{datos_estudiante}* fue eliminado de *{chat.title}*.",
            parse_mode='Markdown'
        )
        
        # Limpiar contexto
        context.user_data.pop('datos_eliminar', None)
        context.user_data.pop('eliminando_de_grupo', None)
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error al eliminar al estudiante. "
            f"Verifica que el bot tenga permisos de administrador.\n\n"
            f"Error: {str(e)}"
        )