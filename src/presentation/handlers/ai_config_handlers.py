from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.config import Config
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.infrastructure.ai.deepseek_adapter import DeepSeekAdapter
from src.presentation.handlers.auth_handlers import probar_conexion_gemini

async def gemini_api_key_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /geminiapikey"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    if not context.args:
        key = Config.GEMINI_API_KEY
        if key:
            masked_key = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            exito, resp = probar_conexion_gemini(key)
            estado = "✅ LISTA PARA SU USO" if exito else f"❌ ERROR: {resp}"
            await update.message.reply_text(
                f"🤖 *Google Gemini - Clave API*\n\n"
                f"• Estado: {estado}\n"
                f"• Clave: `{masked_key}`\n"
                f"• Modelo: `{Config.GEMINI_MODEL}`\n\n"
                f"Para cambiarla: `/geminiapikey TU_NUEVA_CLAVE`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"🤖 *Google Gemini - Clave API*\n\n"
                f"• Estado: ❌ *Sin clave configurada*\n\n"
                f"Para configurar: `/geminiapikey TU_CLAVE`",
                parse_mode='Markdown'
            )
        return

    nueva_key = context.args[0].strip()
    if len(nueva_key) < 10:
        await update.message.reply_text("❌ La clave de API ingresada parece ser inválida.")
        return

    msg = await update.message.reply_text("⏳ Verificando clave de Gemini con solicitud de prueba...")
    exito, resp = probar_conexion_gemini(nueva_key)
    masked_key = nueva_key[:4] + "..." + nueva_key[-4:] if len(nueva_key) > 8 else "****"

    if exito:
        Config.set_gemini_api_key(nueva_key)
        try:
            db.guardar_config('GEMINI_API_KEY', nueva_key)
        except Exception as e:
            print(f"⚠️ Error al guardar GEMINI_API_KEY en BD: {e}")
        await msg.edit_text(
            f"✅ *¡API de Gemini verificada y lista!*\n\n"
            f"• Clave: `{masked_key}`\n"
            f"• Respuesta de prueba: _\"{resp}\"_\n"
            f"• Persistencia: Guardada en BD y `.env`",
            parse_mode='Markdown'
        )
    else:
        await msg.edit_text(
            f"❌ *Error al verificar la clave de Gemini:*\n`{resp}`",
            parse_mode='Markdown'
        )

async def gemini_model_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /geminimodel"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    if not context.args:
        await update.message.reply_text(
            f"🤖 *Google Gemini - Modelo Actual*\n\n"
            f"• Modelo en uso: `{Config.GEMINI_MODEL}`\n\n"
            f"Para cambiar el modelo, envía:\n`/geminimodel NOMBRE_MODELO`\n"
            f"Ejemplos: `gemini-flash-latest`, `gemini-1.5-flash`, `gemini-2.0-flash`",
            parse_mode='Markdown'
        )
        return

    nuevo_modelo = context.args[0].strip()
    Config.set_gemini_model(nuevo_modelo)
    try:
        db.guardar_config('GEMINI_MODEL', nuevo_modelo)
    except Exception as e:
        print(f"⚠️ Error al guardar GEMINI_MODEL en BD: {e}")

    await update.message.reply_text(
        f"✅ *Modelo de Gemini actualizado con éxito:*\n`{nuevo_modelo}`",
        parse_mode='Markdown'
    )

async def deepseek_api_key_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /deepseekapikey"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    if not context.args:
        key = Config.DEEPSEEK_API_KEY
        if key:
            masked_key = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            exito, resp = DeepSeekAdapter.probar_conexion(key, Config.DEEPSEEK_MODEL)
            estado = "✅ LISTA PARA SU USO" if exito else f"❌ ERROR: {resp}"
            await update.message.reply_text(
                f"🐳 *DeepSeek - Clave API*\n\n"
                f"• Estado: {estado}\n"
                f"• Clave: `{masked_key}`\n"
                f"• Modelo: `{Config.DEEPSEEK_MODEL}`\n\n"
                f"Para cambiarla: `/deepseekapikey TU_NUEVA_CLAVE`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"🐳 *DeepSeek - Clave API*\n\n"
                f"• Estado: ❌ *Sin clave configurada*\n\n"
                f"Para configurar: `/deepseekapikey TU_CLAVE`",
                parse_mode='Markdown'
            )
        return

    nueva_key = context.args[0].strip()
    if len(nueva_key) < 10:
        await update.message.reply_text("❌ La clave de API ingresada parece ser inválida.")
        return

    msg = await update.message.reply_text("⏳ Verificando clave de DeepSeek con solicitud de prueba...")
    exito, resp = DeepSeekAdapter.probar_conexion(nueva_key, Config.DEEPSEEK_MODEL)
    masked_key = nueva_key[:4] + "..." + nueva_key[-4:] if len(nueva_key) > 8 else "****"

    if exito:
        Config.set_deepseek_api_key(nueva_key)
        try:
            db.guardar_config('DEEPSEEK_API_KEY', nueva_key)
        except Exception as e:
            print(f"⚠️ Error al guardar DEEPSEEK_API_KEY en BD: {e}")
        await msg.edit_text(
            f"✅ *¡API de DeepSeek verificada y lista!*\n\n"
            f"• Clave: `{masked_key}`\n"
            f"• Respuesta de prueba: _\"{resp}\"_\n"
            f"• Persistencia: Guardada en BD y `.env`",
            parse_mode='Markdown'
        )
    else:
        await msg.edit_text(
            f"❌ *Error al verificar la clave de DeepSeek:*\n`{resp}`",
            parse_mode='Markdown'
        )

async def deepseek_model_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /deepseekmodel"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    if not context.args:
        await update.message.reply_text(
            f"🐳 *DeepSeek - Modelo Actual*\n\n"
            f"• Modelo en uso: `{Config.DEEPSEEK_MODEL}`\n\n"
            f"Para cambiar el modelo, envía:\n`/deepseekmodel NOMBRE_MODELO`\n"
            f"Ejemplos: `deepseek-chat`, `deepseek-reasoner`, `deepseek-coder`",
            parse_mode='Markdown'
        )
        return

    nuevo_modelo = context.args[0].strip()
    Config.set_deepseek_model(nuevo_modelo)
    try:
        db.guardar_config('DEEPSEEK_MODEL', nuevo_modelo)
    except Exception as e:
        print(f"⚠️ Error al guardar DEEPSEEK_MODEL en BD: {e}")

    await update.message.reply_text(
        f"✅ *Modelo de DeepSeek actualizado con éxito:*\n`{nuevo_modelo}`",
        parse_mode='Markdown'
    )

def construir_menu_modelos_texto() -> tuple[str, InlineKeyboardMarkup]:
    """Genera el texto y teclado interactivo del menú /model"""
    active = Config.ACTIVE_AI_PROVIDER.lower()
    
    gemini_key = Config.GEMINI_API_KEY
    gemini_mask = gemini_key[:4] + "..." + gemini_key[-4:] if len(gemini_key) > 8 else "No configurada"
    
    deepseek_key = Config.DEEPSEEK_API_KEY
    deepseek_mask = deepseek_key[:4] + "..." + deepseek_key[-4:] if len(deepseek_key) > 8 else "No configurada"

    btn_gemini = "🟢 Google Gemini (ACTIVO)" if active == "gemini" else "🤖 Activar Gemini"
    btn_deepseek = "🟢 DeepSeek (ACTIVO)" if active == "deepseek" else "🐳 Activar DeepSeek"

    texto = (
        f"🧠 *GESTIÓN DE MODELOS E INTELIGENCIA ARTIFICIAL*\n\n"
        f"• *Proveedor Activo en el Bot:* **{Config.ACTIVE_AI_PROVIDER.upper()}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Google Gemini*\n"
        f"• Clave: `{gemini_mask}`\n"
        f"• Modelo: `{Config.GEMINI_MODEL}`\n\n"
        f"🐳 *DeepSeek*\n"
        f"• Clave: `{deepseek_mask}`\n"
        f"• Modelo: `{Config.DEEPSEEK_MODEL}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Elige con cuál modelo trabajará el bot o consulta comandos:*"
    )

    keyboard = [
        [
            InlineKeyboardButton(btn_gemini, callback_data="select_ai_provider_gemini"),
            InlineKeyboardButton(btn_deepseek, callback_data="select_ai_provider_deepseek")
        ],
        [
            InlineKeyboardButton("⚙️ Guía de Comandos de Configuración", callback_data="menu_ai_comandos_guia")
        ],
        [
            InlineKeyboardButton("🔙 Menú Principal", callback_data="volver_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return texto, reply_markup

async def model_menu_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /model"""
    user = update.effective_user
    db = context.bot_data['db']

    if not db.es_profesor_verificado(user.id):
        await update.message.reply_text("⚠️ Este comando solo está disponible para profesores verificados.")
        return

    texto, reply_markup = construir_menu_modelos_texto()
    await update.message.reply_text(texto, parse_mode='Markdown', reply_markup=reply_markup)

async def callback_model_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las interacciones del menú interactivo /model"""
    query = update.callback_query
    await query.answer()
    data = query.data
    db = context.bot_data['db']

    if data.startswith("select_ai_provider_"):
        prov = data.replace("select_ai_provider_", "")
        Config.set_active_ai_provider(prov)
        try:
            db.guardar_config('ACTIVE_AI_PROVIDER', prov)
        except Exception as e:
            print(f"⚠️ Error al guardar ACTIVE_AI_PROVIDER en BD: {e}")
        
        texto, reply_markup = construir_menu_modelos_texto()
        await query.edit_message_text(
            f"✅ *¡Proveedor activado:* {prov.upper()}!\n\n" + texto,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    elif data == "menu_ai_comandos_guia":
        guia_texto = (
            "⚙️ *GUÍA DE COMANDOS DE CONFIGURACIÓN DE IA:*\n\n"
            "🤖 *Google Gemini:*\n"
            "• Configurar Clave: `/geminiapikey TU_CLAVE`\n"
            "• Configurar Modelo: `/geminimodel NOMBRE_MODELO`\n"
            "  _(ej. `gemini-flash-latest`, `gemini-1.5-flash`)_\n\n"
            "🐳 *DeepSeek:*\n"
            "• Configurar Clave: `/deepseekapikey TU_CLAVE`\n"
            "• Configurar Modelo: `/deepseekmodel NOMBRE_MODELO`\n"
            "  _(ej. `deepseek-chat`, `deepseek-reasoner`)_\n\n"
            "💡 Usa `/model` en cualquier momento para cambiar de proveedor."
        )
        keyboard = [[InlineKeyboardButton("🔙 Volver al Menú de Modelos", callback_data="select_ai_provider_" + Config.ACTIVE_AI_PROVIDER)]]
        await query.edit_message_text(guia_texto, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
