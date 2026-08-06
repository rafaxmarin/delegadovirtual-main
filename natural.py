from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ContextTypes # type: ignore
from gemini_handler import GeminiHandler

async def procesar_mensaje_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ÚNICO handler de mensajes privados - Redirige según el flujo activo"""
    user = update.effective_user
    message = update.message
    db = context.bot_data['db']
    
    if not db.es_profesor_verificado(user.id):
        return
    if update.effective_chat.type != 'private':
        return
    if not message.text:
        return
    
    texto = message.text.strip()
    print(f"⚪ MENSAJE RECIBIDO: '{texto[:80]}'")
    
    # Verificar flujos activos EN ORDEN
    if context.user_data.get('creando_recaudacion'):
        print("⚪ → Redirigiendo a RECAUDACIÓN")
        from handlers.recaudacion import procesar_recaudacion
        await procesar_recaudacion(update, context)
        return
    
    if context.user_data.get('esperando_anuncio'):
        print("⚪ → Redirigiendo a ANUNCIO")
        from handlers.anuncios import recibir_anuncio
        await recibir_anuncio(update, context)
        return
    
    if context.user_data.get('esperando_minuta'):
        print("⚪ → Redirigiendo a MINUTA")
        from handlers.minuta import recibir_contenido_minuta
        await recibir_contenido_minuta(update, context)
        return
    
    if context.user_data.get('esperando_material'):
        print("⚪ → Redirigiendo a MATERIAL")
        from handlers.material import recibir_material
        await recibir_material(update, context)
        return
    
    if context.user_data.get('esperando_reglamento'):
        print("⚪ → Redirigiendo a REGLAMENTO")
        from handlers.reglamento import recibir_reglamento
        await recibir_reglamento(update, context)
        return
    
    if context.user_data.get('agregando_alumno'):
        print("⚪ → Redirigiendo a AGREGAR ALUMNO")
        from handlers.alumnos import recibir_datos_alumno
        await recibir_datos_alumno(update, context)
        return
    
    if context.user_data.get('esperando_datos_eliminar'):
        print("⚪ → Redirigiendo a ELIMINAR ALUMNO")
        from handlers.alumnos import recibir_datos_eliminar
        await recibir_datos_eliminar(update, context)
        return
    
    if context.user_data.get('respondiendo_asesoria'):
        print("⚪ → Redirigiendo a ASESORÍA")
        from handlers.asesoria import recibir_respuesta_asesoria
        await recibir_respuesta_asesoria(update, context)
        return
    
    # Cancelar
    if texto.lower() in ['cancelar', 'cancel', 'salir']:
        for k in list(context.user_data.keys()):
            context.user_data.pop(k, None)
        await message.reply_text("✅ Cancelado. Usa /menu.")
        return
    
    # Conversación natural
    try:
        intencion = GeminiHandler.interpretar_intencion(texto)
        funciones = {'1': 'Estado de grupos', '2': 'Recaudación', '3': 'Emitir anuncio',
                     '4': 'Redactar minuta', '5': 'Compartir material', '6': 'Buzón de asesoría'}
        if intencion in funciones:
            await message.reply_text(f"🤔 Quieres: *{funciones[intencion]}*\nUsa /menu.", parse_mode='Markdown')
        else:
            respuesta = GeminiHandler.responder_conversacion(texto)
            await message.reply_text(respuesta)
    except:
        await message.reply_text("Usa /menu para ver las opciones.")
