import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, ChatJoinRequestHandler, filters
from src.config import Config
from src.infrastructure.database.factory import get_repository

from src.presentation.handlers.auth_handlers import start, button_auth, verificar_password, config_api_comando
from src.presentation.handlers.menu_handlers import (
    menu, volver_menu, cerrar_menu, estudiante_recaudacion_callback,
    estudiante_guia_pago_callback, estudiante_guia_pregunta_callback,
    estudiante_guia_anuncios_callback, estudiante_guia_material_callback,
    estudiante_guia_reglamento_callback
)
from src.presentation.handlers.grupo_handlers import (
    estado_grupos, detalle_grupo, detectar_agregacion_grupo, manejar_respuesta_grupo,
    confirmar_desvincular_grupo, ejecutar_desvincular_grupo, solicitar_cedula_nuevo_estudiante,
    confirmar_limpiar_chat, ejecutar_limpiar_chat
)
from src.presentation.handlers.recaudacion_handlers import (
    menu_recaudacion, iniciar_recaudacion, procesar_recaudacion, confirmar_recaudacion,
    enviar_recaudacion, validar_comprobante, verificar_fechas_limite_job,
    ver_reporte_recaudacion_menu, ver_reporte_recaudacion_grupo, consultar_recaudacion_comando,
    registrar_pago_efectivo, copiar_datos_pago_callback
)
from src.presentation.handlers.minuta_handlers import redactar_minuta, recibir_contenido_minuta, generar_minuta_formato, enviar_minuta_grupo, despachar_minuta
from src.presentation.handlers.asesoria_handlers import buzon_asesoria, responder_asesoria, ignorar_asesoria, detectar_solicitud_estudiante, enviar_pregunta_asesoria
from src.presentation.handlers.strike_handlers import control_strikes, ver_historial_strikes, monitorear_mensajes
from src.presentation.handlers.alumno_handlers import agregar_alumno, invitar_alumno_grupo, eliminar_alumno, listar_estudiantes_grupo, confirmar_eliminar_alumno
from src.presentation.handlers.material_handlers import compartir_material, confirmar_material, enviar_material
from src.presentation.handlers.anuncio_handlers import emitir_anuncio, confirmar_anuncio, enviar_anuncio_grupo
from src.presentation.handlers.reglamento_handlers import fijar_reglamento, confirmar_reglamento, fijar_reglamento_grupo
from src.presentation.handlers.natural_handlers import procesar_mensaje_natural
from src.presentation.handlers.verificacion_handlers import (
    verificar_miembros_menu, seleccionar_grupo_verificacion,
    notificar_grupo_verificacion, verificar_pendientes_job
)
from src.presentation.handlers.join_request_handlers import procesar_solicitud_ingreso
from src.presentation.handlers.ai_config_handlers import (
    gemini_api_key_comando, gemini_model_comando,
    deepseek_api_key_comando, deepseek_model_comando,
    model_menu_comando, callback_model_menu
)

def main():
    Config.validate()
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN no encontrado. Revisa tu archivo .env")
        return

    print(f"🤖 Iniciando {Config.APP_NAME} v{Config.VERSION} (Clean & Hexagonal Architecture)...")
    db = get_repository()

    # Restaurar configuraciones de IA desde la base de datos si existen
    prov_db = db.obtener_config('ACTIVE_AI_PROVIDER')
    if prov_db: Config.set_active_ai_provider(prov_db)

    gem_key_db = db.obtener_config('GEMINI_API_KEY')
    if gem_key_db: Config.set_gemini_api_key(gem_key_db)

    gem_model_db = db.obtener_config('GEMINI_MODEL')
    if gem_model_db: Config.set_gemini_model(gem_model_db)

    ds_key_db = db.obtener_config('DEEPSEEK_API_KEY')
    if ds_key_db: Config.set_deepseek_api_key(ds_key_db)

    ds_model_db = db.obtener_config('DEEPSEEK_MODEL')
    if ds_model_db: Config.set_deepseek_model(ds_model_db)

    application = Application.builder().token(token).read_timeout(30).write_timeout(30).build()
    application.bot_data['db'] = db

    # COMANDOS GENERALES Y DE IA
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(CommandHandler('pregunta', enviar_pregunta_asesoria))
    application.add_handler(CommandHandler('pago', validar_comprobante))
    application.add_handler(CommandHandler('efectivo', registrar_pago_efectivo))
    application.add_handler(CommandHandler('recaudacion', consultar_recaudacion_comando))
    application.add_handler(CommandHandler('api', config_api_comando))

    # COMANDOS DE CONFIGURACIÓN DE IA (GEMINI Y DEEPSEEK)
    application.add_handler(CommandHandler('geminiapikey', gemini_api_key_comando))
    application.add_handler(CommandHandler('geminimodel', gemini_model_comando))
    application.add_handler(CommandHandler('deepseekapikey', deepseek_api_key_comando))
    application.add_handler(CommandHandler('deepseekmodel', deepseek_model_comando))
    application.add_handler(CommandHandler('model', model_menu_comando))

    # CALLBACKS DE GESTIÓN DE IA
    application.add_handler(CallbackQueryHandler(callback_model_menu, pattern='^(select_ai_provider_|menu_ai_comandos_guia)'))

    # CALLBACKS DEL MENÚ Y NAVEGACIÓN
    application.add_handler(CallbackQueryHandler(button_auth, pattern='^(soy_profesor|no_profesor)$'))
    application.add_handler(CallbackQueryHandler(estado_grupos, pattern='^menu_estado_grupos$'))
    application.add_handler(CallbackQueryHandler(menu_recaudacion, pattern='^menu_recaudacion$'))

    application.add_handler(CallbackQueryHandler(iniciar_recaudacion, pattern='^iniciar_crear_recaudacion$'))
    application.add_handler(CallbackQueryHandler(ver_reporte_recaudacion_menu, pattern='^ver_reporte_recaudacion_menu$'))
    application.add_handler(CallbackQueryHandler(ver_reporte_recaudacion_grupo, pattern='^reporte_rec_grupo_'))
    application.add_handler(CallbackQueryHandler(emitir_anuncio, pattern='^menu_anuncio$'))
    application.add_handler(CallbackQueryHandler(redactar_minuta, pattern='^menu_minuta$'))
    application.add_handler(CallbackQueryHandler(compartir_material, pattern='^menu_material$'))
    application.add_handler(CallbackQueryHandler(buzon_asesoria, pattern='^menu_asesoria$'))
    application.add_handler(CallbackQueryHandler(control_strikes, pattern='^menu_strikes$'))
    application.add_handler(CallbackQueryHandler(fijar_reglamento, pattern='^menu_reglamento$'))
    application.add_handler(CallbackQueryHandler(agregar_alumno, pattern='^menu_agregar$'))
    application.add_handler(CallbackQueryHandler(eliminar_alumno, pattern='^menu_eliminar$'))
    application.add_handler(CallbackQueryHandler(verificar_miembros_menu, pattern='^menu_verificar_miembros$'))
    application.add_handler(CallbackQueryHandler(volver_menu, pattern='^volver_menu$'))
    application.add_handler(CallbackQueryHandler(cerrar_menu, pattern='^menu_cerrar$'))

    # CALLBACKS MENÚ DE ESTUDIANTES
    application.add_handler(CallbackQueryHandler(estudiante_guia_anuncios_callback, pattern='^estudiante_guia_anuncios$'))
    application.add_handler(CallbackQueryHandler(estudiante_guia_material_callback, pattern='^estudiante_guia_material$'))
    application.add_handler(CallbackQueryHandler(estudiante_recaudacion_callback, pattern='^estudiante_recaudacion$'))
    application.add_handler(CallbackQueryHandler(estudiante_guia_reglamento_callback, pattern='^estudiante_guia_reglamento$'))
    application.add_handler(CallbackQueryHandler(estudiante_guia_pago_callback, pattern='^estudiante_guia_pago$'))
    application.add_handler(CallbackQueryHandler(estudiante_guia_pregunta_callback, pattern='^estudiante_guia_pregunta$'))

    # CALLBACKS DE GRUPOS
    application.add_handler(CallbackQueryHandler(detalle_grupo, pattern='^detalle_grupo_'))
    application.add_handler(CallbackQueryHandler(manejar_respuesta_grupo, pattern='^(aceptar_grupo_|rechazar_grupo_)'))
    application.add_handler(CallbackQueryHandler(confirmar_desvincular_grupo, pattern='^desvincular_grupo_'))
    application.add_handler(CallbackQueryHandler(ejecutar_desvincular_grupo, pattern='^confirmar_desvincular_'))
    application.add_handler(CallbackQueryHandler(confirmar_limpiar_chat, pattern='^limpiar_chat_'))
    application.add_handler(CallbackQueryHandler(ejecutar_limpiar_chat, pattern='^confirmar_limpiar_chat_exec_'))

    # CALLBACKS DE ANUNCIOS
    application.add_handler(CallbackQueryHandler(confirmar_anuncio, pattern='^confirmar_anuncio$'))
    application.add_handler(CallbackQueryHandler(enviar_anuncio_grupo, pattern='^enviar_anuncio_'))

    # CALLBACKS DE RECAUDACIÓN
    application.add_handler(CallbackQueryHandler(confirmar_recaudacion, pattern='^confirmar_recaudacion$'))
    application.add_handler(CallbackQueryHandler(enviar_recaudacion, pattern='^enviar_recaudacion_'))
    application.add_handler(CallbackQueryHandler(copiar_datos_pago_callback, pattern='^copiar_datos_pago_'))

    # CALLBACKS DE MINUTA
    application.add_handler(CallbackQueryHandler(generar_minuta_formato, pattern='^formato_'))
    application.add_handler(CallbackQueryHandler(enviar_minuta_grupo, pattern='^enviar_minuta_grupo$'))
    application.add_handler(CallbackQueryHandler(despachar_minuta, pattern='^despachar_minuta_'))

    # CALLBACKS DE MATERIAL
    application.add_handler(CallbackQueryHandler(confirmar_material, pattern='^confirmar_material$'))
    application.add_handler(CallbackQueryHandler(enviar_material, pattern='^enviar_material_'))

    # CALLBACKS DE ASESORÍA
    application.add_handler(CallbackQueryHandler(responder_asesoria, pattern='^responder_asesoria_'))
    application.add_handler(CallbackQueryHandler(ignorar_asesoria, pattern='^ignorar_asesoria_'))

    # CALLBACKS DE STRIKES
    application.add_handler(CallbackQueryHandler(ver_historial_strikes, pattern='^ver_strikes_'))

    # CALLBACKS DE REGLAMENTO
    application.add_handler(CallbackQueryHandler(confirmar_reglamento, pattern='^confirmar_reglamento$'))
    application.add_handler(CallbackQueryHandler(fijar_reglamento_grupo, pattern='^fijar_reglamento_'))

    # CALLBACKS DE ALUMNOS
    application.add_handler(CallbackQueryHandler(invitar_alumno_grupo, pattern='^invitar_alumno_'))
    application.add_handler(CallbackQueryHandler(listar_estudiantes_grupo, pattern='^listar_estudiantes_'))
    application.add_handler(CallbackQueryHandler(confirmar_eliminar_alumno, pattern='^confirmar_eliminar_alumno_'))

    # CALLBACKS DE VERIFICACIÓN DE MIEMBROS
    application.add_handler(CallbackQueryHandler(seleccionar_grupo_verificacion, pattern='^cargar_verificacion_'))
    application.add_handler(CallbackQueryHandler(notificar_grupo_verificacion, pattern='^notificar_verificacion_'))

    # SOLICITUDES DE INGRESO A GRUPOS (ChatJoinRequest)
    application.add_handler(ChatJoinRequestHandler(procesar_solicitud_ingreso))

    # MENSAJES EN GRUPOS
    application.add_handler(ChatMemberHandler(detectar_agregacion_grupo, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, solicitar_cedula_nuevo_estudiante))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Regex(r'(?i)@'), detectar_solicitud_estudiante))
    application.add_handler(MessageHandler(filters.CaptionRegex(r'(?i)/pago') & filters.ChatType.GROUPS, validar_comprobante))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, monitorear_mensajes))

    # MENSAJES PRIVADOS (Atiende texto, documentos, fotos o cualquier contenido según estado)
    application.add_handler(MessageHandler(
        ~filters.COMMAND & filters.ChatType.PRIVATE,
        procesar_mensaje_natural
    ))

    # Jobs periódicos (Revisión de fechas límite cada 5 min y verificación de pendientes cada 3 min)
    if application.job_queue:
        application.job_queue.run_repeating(verificar_fechas_limite_job, interval=300, first=15)
        application.job_queue.run_repeating(verificar_pendientes_job, interval=180, first=30)  # Cada 3 min

    print("🚀 Delegado Virtual iniciado exitosamente!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
