from telegram import Update
from telegram.ext import ContextTypes
from src.config import Config
from src.presentation.keyboards import get_auth_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start - Inicio del bot"""
    user = update.effective_user
    db = context.bot_data['db']
    
    # Manejar inicio con parámetros de verificación de grupo (start=verificar_<chat_id>)
    if context.args and context.args[0].startswith("verificar_"):
        try:
            chat_id = int(context.args[0].replace("verificar_", ""))
            context.user_data['esperando_cedula_grupo'] = chat_id
            
            nombre_grupo = "tu materia"
            try:
                chat = await context.bot.get_chat(chat_id)
                if chat and chat.title:
                    nombre_grupo = chat.title
            except Exception:
                pass
                
            await update.message.reply_text(
                f"🔐 *VERIFICACIÓN DE ESTUDIANTE*\n\n"
                f"Para verificar tu acceso a *{nombre_grupo}*, por favor ingresa tu número de *Cédula* (solo números, ej: `12345678`):",
                parse_mode='Markdown'
            )
            return
        except ValueError:
            pass

    if db.es_profesor_verificado(user.id):
        await update.message.reply_text(
            f"👋 ¡Bienvenido de nuevo, {user.first_name}!\n\n"
            "Escribe /menu para ver las opciones disponibles o "
            "simplemente dime qué necesitas hacer."
        )
        return
    
    db.registrar_profesor(user.id, user.username or user.first_name)
    
    await update.message.reply_text(
        "👋 *Bienvenido al Delegado Virtual — UDO Monagas*\n\n"
        "🎓 *Si eres estudiante:* Ingresa a tu materia utilizando el enlace de invitación de tu profesor o escribe tu número de *Cédula* para verificar tu inscripción.\n\n"
        "👨‍🏫 *Si eres profesor:* Presiona el botón de abajo para verificar tu acceso con contraseña.",
        parse_mode='Markdown',
        reply_markup=get_auth_keyboard()
    )

async def button_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones de autenticación"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "no_profesor":
        await query.edit_message_text(
            "Lo siento, este bot es exclusivo para profesores de la UDO Monagas. "
            "Si eres estudiante, por favor contacta a tu profesor por otras vías.\n\n"
            "¡Gracias por tu interés!"
        )
        return
    
    if query.data == "soy_profesor":
        await query.edit_message_text(
            "🔐 Para verificar tu identidad como profesor, "
            "por favor ingresa la contraseña:"
        )
        context.user_data['esperando_password'] = True

async def verificar_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica la contraseña ingresada"""
    password_ingresado = update.message.text.strip()
    password_correcto = Config.PROFESOR_PASSWORD
    user = update.effective_user
    db = context.bot_data['db']
    
    if password_ingresado == password_correcto:
        db.verificar_profesor(user.id)
        context.user_data['esperando_password'] = False
        
        await update.message.reply_text(
            "✅ *¡Acceso validado correctamente!*\n\n"
            "Bienvenido al *Delegado Virtual*, tu asistente para gestionar "
            "la comunicación con tus estudiantes de manera fácil y eficiente.\n\n"
            "🎯 *Funcionalidades principales:*\n"
            "• Enviar anuncios y material de estudio\n"
            "• Gestionar recaudaciones\n"
            "• Redactar minutas formales\n"
            "• Control de asistencia y strikes\n"
            "• Buzón de asesoría\n"
            "• Y mucho más...\n\n"
            "💡 *Modo de uso:*\n"
            "• Escribe /menu para ver todas las opciones\n"
            "• O simplemente dime qué necesitas y yo te ayudo\n\n"
            "¡Comencemos! 🚀",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Contraseña incorrecta. No se puede validar tu acceso como profesor.\n\n"
            "Si eres profesor de la UDO Monagas y no conoces la contraseña, "
            "por favor contacta al administrador del sistema."
        )
        context.user_data['esperando_password'] = False

def probar_conexion_gemini(api_key: str):
    """Realiza una petición de prueba a Gemini para verificar que reciba respuesta"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = getattr(Config, 'GEMINI_MODEL', 'gemini-flash-latest')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Responde únicamente con la palabra 'OK'")
        if response and response.text:
            return True, response.text.strip()
        return False, "La API no devolvió texto en la respuesta de prueba."
    except Exception as e:
        return False, str(e)

async def config_api_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /api para consultar o configurar la clave API de Gemini probando su respuesta"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    # Si no se pasó argumento, verificar y mostrar estado de la API actual
    if not context.args:
        key = Config.GEMINI_API_KEY
        if key:
            masked_key = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            exito, respuesta = probar_conexion_gemini(key)
            if exito:
                await update.message.reply_text(
                    f"🔑 *Estado de la API de Gemini*\n\n"
                    f"• Estado: ✅ *LA API ESTÁ LISTA PARA SU USO*\n"
                    f"• Clave actual: `{masked_key}`\n"
                    f"• Respuesta de prueba: _\"{respuesta}\"_\n\n"
                    f"Para cambiarla, envía:\n`/api TU_NUEVA_CLAVE_API`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"🔑 *Estado de la API de Gemini*\n\n"
                    f"• Estado: ❌ *LA API NO ESTÁ LISTA PARA SU USO*\n"
                    f"• Clave actual: `{masked_key}`\n"
                    f"• Detalle de error: `{respuesta}`\n\n"
                    f"Para actualizarla por una clave válida, envía:\n`/api TU_NUEVA_CLAVE_API`",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                f"🔑 *Estado de la API de Gemini*\n\n"
                f"• Estado: ❌ *LA API NO ESTÁ LISTA PARA SU USO (Sin clave)*\n\n"
                f"Para subir y activar la API de Gemini, envía:\n"
                f"`/api TU_CLAVE_API`",
                parse_mode='Markdown'
            )
        return

    # Si se proporciona una nueva clave
    nueva_key = context.args[0].strip()
    if len(nueva_key) < 10:
        await update.message.reply_text("❌ La clave de API ingresada parece ser inválida o demasiado corta.")
        return

    mensaje_espera = await update.message.reply_text("⏳ Verificando la clave realizando una consulta de prueba a Gemini...")

    exito, respuesta = probar_conexion_gemini(nueva_key)
    masked_key = nueva_key[:4] + "..." + nueva_key[-4:] if len(nueva_key) > 8 else "****"

    if exito:
        Config.set_gemini_api_key(nueva_key)
        try:
            db.guardar_config('GEMINI_API_KEY', nueva_key)
        except Exception as e:
            print(f"⚠️ No se pudo guardar clave en BD SQLite: {e}")

        await mensaje_espera.edit_text(
            f"✅ *¡LA API ESTÁ LISTA PARA SU USO!*\n\n"
            f"• Estado: *Conectada y verificada*\n"
            f"• Clave activada: `{masked_key}`\n"
            f"• Respuesta de prueba recibida: _\"{respuesta}\"_\n"
            f"• Persistencia: Guardada en base de datos y configuración (`.env`)\n\n"
            f"El bot ya puede hacer uso de todas las funciones de Inteligencia Artificial 🤖",
            parse_mode='Markdown'
        )

    else:
        await mensaje_espera.edit_text(
            f"❌ *¡LA API NO ESTÁ LISTA PARA SU USO!*\n\n"
            f"No se pudo recibir la respuesta de prueba de Gemini.\n"
            f"• Detalle del error: `{respuesta}`\n\n"
            f"Por favor verifica que la clave ingresada sea correcta y tenga cuota/permisos disponibles.",
            parse_mode='Markdown'
        )


