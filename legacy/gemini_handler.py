import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

class GeminiHandler:
    @staticmethod
    def estructurar_texto_formal(texto):
        """Convierte texto informal en un anuncio formal y respetuoso"""
        prompt = f"""
        Eres un asistente que convierte mensajes informales en anuncios formales 
        para un entorno universitario. El tono debe ser respetuoso, profesional y claro.
        
        Mensaje original: {texto}
        
        Conviértelo en un anuncio formal. Solo responde con el texto formateado, sin comillas ni notas adicionales.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def transcribir_y_estructurar(texto_o_transcripcion):
        """Transcribe nota de voz y estructura formalmente"""
        prompt = f"""
        Estructura el siguiente texto de manera formal y profesional para un entorno universitario.
        Corrige errores, mejora la redacción y mantén un tono respetuoso.
        
        Texto: {texto_o_transcripcion}
        
        Solo responde con el texto estructurado, sin comillas ni notas.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def generar_minuta_apa(contenido, formato):
        """Genera contenido de minuta con formato APA 7ma edición"""
        prompt = f"""
        Redacta una minuta académica basada en el siguiente contenido.
        Debe seguir las normas APA 7ma edición.
        El formato solicitado es: {formato}
        
        Contenido: {contenido}
        
        Incluye: título, introducción, desarrollo, conclusión y referencias si aplica.
        Solo responde con el contenido estructurado.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def generar_mensaje_introductorio(material_descripcion):
        """Genera un mensaje introductorio para material de estudio"""
        prompt = f"""
        Crea un breve mensaje introductorio (2-3 líneas) para presentar 
        el siguiente material de estudio a estudiantes universitarios.
        
        Material: {material_descripcion}
        
        Solo responde con el mensaje, sin comillas ni notas.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def analizar_comprobante_imagen(foto):
        """Analiza una imagen de comprobante de pago"""
        prompt = """
        Analiza esta imagen de comprobante de pago móvil y extrae:
        - Nombre y apellido del pagador
        - Fecha y hora del pago
        - Banco, cédula y teléfono del beneficiario
        
        Responde en formato JSON.
        """
        response = model.generate_content([prompt, foto])
        return response.text.strip()
    
    @staticmethod
    def interpretar_intencion(mensaje):
        """Interpreta la intención del profesor en lenguaje natural"""
        prompt = f"""
        Eres un asistente de un bot de Telegram para profesores universitarios.
        El bot tiene estas funciones:
        1. estado_grupos - Ver estado de los grupos
        2. recaudacion - Crear recaudación
        3. emitir_anuncio - Enviar anuncio
        4. redactar_minuta - Redactar minuta
        5. compartir_material - Compartir material
        6. buzon_asesoria - Buzón de asesoría
        7. control_strikes - Control de strikes
        8. fijar_reglamento - Fijar reglamento
        9. agregar_alumno - Agregar alumno
        10. eliminar_alumno - Eliminar alumno
        
        Mensaje del profesor: {mensaje}
        Responde SOLO con el número de la función más probable (1-10) o 0 si no estás seguro.
        Ejemplo: "1"
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def detectar_contenido_inapropiado(mensaje):
        """Detecta si un mensaje contiene contenido inapropiado"""
        prompt = f"""
        Analiza si el siguiente mensaje contiene:
        - Malas palabras u obscenidades
        - Lenguaje ofensivo o discriminatorio
        - Spam o contenido no educativo
        
        Mensaje: {mensaje}
        
        Responde SOLO "SI" o "NO". Si es SI, añade el motivo en una palabra.
        Ejemplo: "SI - obscenidades" o "NO"
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def es_material_inapropiado(descripcion):
        """Determina si un material compartido es inapropiado"""
        prompt = f"""
        Determina si el siguiente contenido es apropiado para un grupo 
        universitario educativo. Considera inapropiado: contenido sexual, 
        violento, spam, o no relacionado con educación.
        
        Contenido: {descripcion}
        
        Responde SOLO "APROPIADO" o "INAPROPIADO".
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    @staticmethod
    def responder_conversacion(mensaje, contexto=""):
        """Responde de manera natural a mensajes del profesor"""
        prompt = f"""
        Eres el Delegado Virtual, un asistente amigable y profesional para 
        profesores de la Universidad de Oriente. Responde de manera cálida,
        útil y concisa al siguiente mensaje.
        
        Contexto: {contexto}
        Mensaje: {mensaje}
        
        Si el mensaje no está relacionado con las funciones del bot, 
        recuérdale amablemente que puede usar /menu para ver las opciones.
        """
        response = model.generate_content(prompt)
        return response.text.strip()