from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import asyncio

async def estado_grupos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el estado de los grupos registrados por el profesor"""
    query = update.callback_query
    user = query.from_user
    db = context.bot_data['db']
    
    grupos = db.obtener_grupos_profesor(user.id)
    
    if not grupos:
        await query.edit_message_text(
            "📊 *ESTADO DE LOS GRUPOS*\n\n"
            "Aún no tienes grupos registrados.\n\n"
            "Agrega el bot a un grupo de Telegram para comenzar.\n"
            "Escribe /menu para volver.",
            parse_mode='Markdown'
        )
        return
    
    mensaje = "📊 *ESTADO DE LOS GRUPOS*\n\n"
    total_estudiantes = 0
    
    for chat_id, nombre in grupos:
        try:
            # Obtener cantidad de miembros del grupo
            miembros = await context.bot.get_chat_member_count(chat_id)
            estudiantes = miembros - 1  # Restar el Delegado Virtual
            total_estudiantes += estudiantes
            mensaje += f"📚 *{nombre}*: {estudiantes} estudiantes\n"
        except TelegramError:
            mensaje += f"📚 *{nombre}*: No se pudo obtener (bot no está en el grupo)\n"
    
    mensaje += f"\n📌 *Total de grupos:* {len(grupos)}"
    mensaje += f"\n👥 *Total de estudiantes:* {total_estudiantes}"
    
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def detectar_agregacion_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando el bot es agregado a un grupo y notifica al profesor"""
    chat = update.effective_chat
    user = update.effective_user
    db = context.bot_data['db']
    
    # Solo procesar si es un grupo o supergrupo
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Verificar si quien agregó al bot es un profesor verificado
    if not db.es_profesor_verificado(user.id):
        # Si no es profesor, salir del grupo
        await context.bot.send_message(
            chat.id,
            "❌ Este bot es exclusivo para profesores de la UDO Monagas. "
            "Saliendo del grupo..."
        )
        await context.bot.leave_chat(chat.id)
        return
    
    # Notificar al profesor en privado
    keyboard = [
        [
            InlineKeyboardButton("✅ Aceptar y registrar", callback_data=f"aceptar_grupo_{chat.id}"),
            InlineKeyboardButton("❌ Rechazar y salir", callback_data=f"rechazar_grupo_{chat.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        user.id,
        f"📢 El Delegado Virtual fue agregado a un nuevo grupo:\n\n"
        f"*Nombre:* {chat.title}\n"
        f"*ID:* {chat.id}\n\n"
        "¿Qué deseas hacer?",
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
            
            # Enviar mensaje al grupo
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

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Estado de grupos", callback_data="menu_estado_grupos"),
            InlineKeyboardButton("💰 Recaudación", callback_data="menu_recaudacion")
        ],
        [
            InlineKeyboardButton("📢 Emitir anuncio", callback_data="menu_anuncio"),
            InlineKeyboardButton("📝 Redactar minuta", callback_data="menu_minuta")
        ],
        [
            InlineKeyboardButton("📚 Compartir material", callback_data="menu_material"),
            InlineKeyboardButton("📬 Buzón de asesoría", callback_data="menu_asesoria")
        ],
        [
            InlineKeyboardButton("⚡ Control de strikes", callback_data="menu_strikes"),
            InlineKeyboardButton("📜 Fijar reglamento", callback_data="menu_reglamento")
        ],
        [
            InlineKeyboardButton("➕ Agregar alumno", callback_data="menu_agregar"),
            InlineKeyboardButton("➖ Eliminar alumno", callback_data="menu_eliminar")
        ],
        [
            InlineKeyboardButton("❌ Cerrar panel", callback_data="menu_cerrar")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 *MENÚ PRINCIPAL - Delegado Virtual*\n\n"
        "Selecciona la función que deseas utilizar:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )