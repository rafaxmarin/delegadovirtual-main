import os
from dotenv import load_dotenv # type: ignore
from telegram import Update # type: ignore
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters # type: ignore
from database import Database

from handlers.auth import start, button_auth, verificar_password
from handlers.menu import menu
from handlers.grupos import (estado_grupos, detectar_agregacion_grupo, manejar_respuesta_grupo, volver_menu)
from handlers.anuncios import (emitir_anuncio, recibir_anuncio, confirmar_anuncio, enviar_anuncio_grupo)
from handlers.recaudacion import (iniciar_recaudacion, procesar_recaudacion, confirmar_recaudacion, enviar_recaudacion, validar_comprobante)
from handlers.minuta import (redactar_minuta, recibir_contenido_minuta, generar_minuta_formato, enviar_minuta_grupo, despachar_minuta)
from handlers.material import (compartir_material, recibir_material, confirmar_material, enviar_material)
from handlers.asesoria import (buzon_asesoria, responder_asesoria, recibir_respuesta_asesoria, ignorar_asesoria, detectar_solicitud_estudiante, enviar_recordatorio_asesoria)
from handlers.strikes import (control_strikes, ver_historial_strikes, eliminar_estudiante_strikes, confirmar_eliminar_estudiante, monitorear_mensajes)
from handlers.reglamento import (fijar_reglamento, recibir_reglamento, confirmar_reglamento, fijar_reglamento_grupo)
from handlers.alumnos import (agregar_alumno, recibir_datos_alumno, invitar_alumno_grupo, eliminar_alumno, listar_estudiantes_grupo, recibir_datos_eliminar, confirmar_eliminar_alumno)
from handlers.natural import procesar_mensaje_natural

load_dotenv()

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN no encontrado")
        return

    print("🤖 Iniciando Delegado Virtual...")
    db = Database()
    print("✅ Base de datos inicializada")

    application = Application.builder().token(token).read_timeout(30).write_timeout(30).build()
    application.bot_data['db'] = db

    # COMANDOS
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', menu))

    # CALLBACKS DEL MENÚ
    application.add_handler(CallbackQueryHandler(button_auth, pattern='^(soy_profesor|no_profesor)$'))
    application.add_handler(CallbackQueryHandler(estado_grupos, pattern='^menu_estado_grupos$'))
    application.add_handler(CallbackQueryHandler(iniciar_recaudacion, pattern='^menu_recaudacion$'))
    application.add_handler(CallbackQueryHandler(emitir_anuncio, pattern='^menu_anuncio$'))
    application.add_handler(CallbackQueryHandler(redactar_minuta, pattern='^menu_minuta$'))
    application.add_handler(CallbackQueryHandler(compartir_material, pattern='^menu_material$'))
    application.add_handler(CallbackQueryHandler(buzon_asesoria, pattern='^menu_asesoria$'))
    application.add_handler(CallbackQueryHandler(control_strikes, pattern='^menu_strikes$'))
    application.add_handler(CallbackQueryHandler(fijar_reglamento, pattern='^menu_reglamento$'))
    application.add_handler(CallbackQueryHandler(agregar_alumno, pattern='^menu_agregar$'))
    application.add_handler(CallbackQueryHandler(eliminar_alumno, pattern='^menu_eliminar$'))
    application.add_handler(CallbackQueryHandler(volver_menu, pattern='^volver_menu$'))

    # CALLBACKS DE GRUPOS
    application.add_handler(CallbackQueryHandler(manejar_respuesta_grupo, pattern='^(aceptar_grupo_|rechazar_grupo_)'))

    # CALLBACKS DE ANUNCIOS
    application.add_handler(CallbackQueryHandler(confirmar_anuncio, pattern='^confirmar_anuncio$'))
    application.add_handler(CallbackQueryHandler(enviar_anuncio_grupo, pattern='^enviar_anuncio_'))

    # CALLBACKS DE RECAUDACIÓN
    application.add_handler(CallbackQueryHandler(confirmar_recaudacion, pattern='^confirmar_recaudacion$'))
    application.add_handler(CallbackQueryHandler(enviar_recaudacion, pattern='^enviar_recaudacion_'))

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
    application.add_handler(CallbackQueryHandler(eliminar_estudiante_strikes, pattern='^eliminar_estudiante_strikes_'))
    application.add_handler(CallbackQueryHandler(confirmar_eliminar_estudiante, pattern='^confirmar_eliminar_'))

    # CALLBACKS DE REGLAMENTO
    application.add_handler(CallbackQueryHandler(confirmar_reglamento, pattern='^confirmar_reglamento$'))
    application.add_handler(CallbackQueryHandler(fijar_reglamento_grupo, pattern='^fijar_reglamento_'))

    # CALLBACKS DE ALUMNOS
    application.add_handler(CallbackQueryHandler(invitar_alumno_grupo, pattern='^invitar_alumno_'))
    application.add_handler(CallbackQueryHandler(listar_estudiantes_grupo, pattern='^listar_estudiantes_'))
    application.add_handler(CallbackQueryHandler(confirmar_eliminar_alumno, pattern='^confirmar_eliminar_alumno_'))

    # MENSAJES EN GRUPOS
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, detectar_agregacion_grupo))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity('mention'), detectar_solicitud_estudiante))
    application.add_handler(MessageHandler(filters.PHOTO, validar_comprobante))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, monitorear_mensajes))

    # =============================================
    # 🔴 SOLUCIÓN: UN SOLO HANDLER PARA PRIVADOS
    # =============================================
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        procesar_mensaje_natural  # Este handler decide a dónde redirigir
    ))

    # Recordatorio cada 48 horas
    application.job_queue.run_repeating(enviar_recordatorio_asesoria, interval=172800, first=10)

    print("🚀 Delegado Virtual iniciado!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__': # type: ignore
    main()
