from telegram import Update
from telegram.ext import ContextTypes
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.presentation.handlers.auth_handlers import verificar_password
from src.presentation.handlers.recaudacion_handlers import procesar_recaudacion
from src.presentation.handlers.minuta_handlers import recibir_contenido_minuta
from src.presentation.handlers.alumno_handlers import recibir_datos_alumno, recibir_datos_eliminar
from src.presentation.handlers.asesoria_handlers import recibir_respuesta_asesoria
from src.presentation.handlers.material_handlers import recibir_material
from src.presentation.handlers.anuncio_handlers import recibir_anuncio
from src.presentation.handlers.reglamento_handlers import recibir_reglamento

gemini = GeminiAdapter()

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
    
    # Si no está verificado y no está ingresando la clave, ignorar
    if not db.es_profesor_verificado(user.id):
        await message.reply_text("🔒 Usa /start para verificar tu acceso como profesor.")
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
