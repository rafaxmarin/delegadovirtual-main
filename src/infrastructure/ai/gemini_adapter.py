import google.generativeai as genai
from typing import Union, Any
import io
from PIL import Image
from src.config import Config

class GeminiAdapter:
    def __init__(self, api_key: str = None, model_name: str = None):
        key = api_key or Config.GEMINI_API_KEY
        if key:
            genai.configure(api_key=key)
        selected_model = model_name or getattr(Config, 'GEMINI_MODEL', 'gemini-flash-latest')
        self.model = genai.GenerativeModel(selected_model)

    def estructurar_texto_formal(self, texto: str) -> str:
        """Convierte texto informal en un anuncio formal y respetuoso"""
        prompt = f"""
        Eres un asistente que convierte mensajes informales en anuncios formales 
        para un entorno universitario. El tono debe ser respetuoso, profesional y claro.
        
        Mensaje original: {texto}
        
        Conviértelo en un anuncio formal. Solo responde con el texto formateado, sin comillas ni notas adicionales.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def transcribir_y_estructurar(self, texto_o_transcripcion: str) -> str:
        """Transcribe nota de voz y estructura formalmente"""
        prompt = f"""
        Estructura el siguiente texto de manera formal y profesional para un entorno universitario.
        Corrige errores, mejora la redacción y mantén un tono respetuoso.
        
        Texto: {texto_o_transcripcion}
        
        Solo responde con el texto estructurado, sin comillas ni notas.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def generar_minuta_apa(self, contenido: str, formato: str) -> str:
        """Genera contenido de minuta con formato APA 7ma edición"""
        prompt = f"""
        Redacta una minuta académica basada en el siguiente contenido.
        Debe seguir las normas APA 7ma edición.
        El formato solicitado es: {formato}
        
        Contenido: {contenido}
        
        Incluye: título, introducción, desarrollo, conclusión y referencias si aplica.
        Solo responde con el contenido estructurado.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def generar_mensaje_introductorio(self, material_descripcion: str) -> str:
        """Genera un mensaje introductorio para material de estudio"""
        prompt = f"""
        Crea un breve mensaje introductorio (2-3 líneas) para presentar 
        el siguiente material de estudio a estudiantes universitarios.
        
        Material: {material_descripcion}
        
        Solo responde con el mensaje, sin comillas ni notas.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def analizar_comprobante_imagen(self, image_input: Union[bytes, Image.Image]) -> str:
        """Analiza una imagen binaria o PIL.Image de comprobante de pago (CORREGIDO TIPO DE DATO)"""
        prompt = """
        Analiza esta imagen de comprobante de pago móvil y extrae:
        - Nombre y apellido del pagador
        - Fecha y hora del pago
        - Banco, cédula y teléfono del beneficiario
        
        Responde en formato JSON.
        """
        if isinstance(image_input, bytes):
            image_obj = Image.open(io.BytesIO(image_input))
        else:
            image_obj = image_input

        response = self.model.generate_content([prompt, image_obj])
        return response.text.strip()
    
    def validar_comprobante_contra_recaudacion(self, image_input: Union[bytes, Image.Image], datos_recaudacion: dict) -> dict:
        """
        Analiza un comprobante de pago con Gemini Vision y lo valida contra los parámetros requeridos.
        Optimizado para comprobantes bancarios venezolanos (BDV / PagomóvilBDV, Banesco, Mercantil, Provincial, etc.).
        """
        import json, re
        prompt = f"""
        Analiza esta captura/comprobante de pago móvil o transferencia bancaria (ej. PagomóvilBDV, Banesco, Mercantil, etc.) y evalúa si cumple los requisitos de la recaudación.

        Parámetros requeridos por la recaudación:
        - Concepto: {datos_recaudacion.get('concepto', '')}
        - Monto esperado: Bs. {datos_recaudacion.get('monto', 0)}
        - Banco destino esperado: {datos_recaudacion.get('banco', '')}
        - Cédula destino esperada: {datos_recaudacion.get('cedula', '')}
        - Teléfono destino esperado: {datos_recaudacion.get('telefono', '')}

        Guía de lectura para comprobantes (especialmente PagomóvilBDV / Banco de Venezuela):
        1. "Operación": Corresponde al número de referencia / comprobante de la transacción (ej. 006852001890).
        2. Recuadro de Monto: Indica la cantidad en Bs. (ej. "497,69 Bs" o "500,00 Bs"). Ten en cuenta los decimales con coma.
        3. "Banco": Es el banco destino o receptor (ej. "0102 - BANCO DE VENEZUELA", "Mercantil", "Banesco", etc.).
           Nota de equivalencia de bancos: "BDV", "Banco de Venezuela" y "0102" son la misma entidad. Lo mismo aplica para otros bancos por su código o nombre.
        4. "Destino": Es el número de teléfono del beneficiario.
        5. "Identificación": Es el número de cédula/R纳入.

        Instrucciones de evaluación:
        1. Extrae:
           - Nombre/titular origen (o usa el concepto si el nombre no es visible)
           - Número de Operación / Referencia
           - Monto pagado en Bs (convertir a número flotante, ej 497.69)
           - Banco destino detectado
           - Fecha y hora de la operación (ej. 31/07/2026)
        2. Requisitos de validez ("valido": true):
           - El banco destino DEBE coincidir con {datos_recaudacion.get('banco', '')} (considerando alias equivalentes como BDV = Banco de Venezuela = 0102).
           - El monto detectado DEBE ser igual o mayor al monto esperado (Bs. {datos_recaudacion.get('monto', 0)}).
           - El número de operación/referencia debe ser legible.
        3. Si no cumple alguno de estos requisitos, marca "valido": false y explica la causa exacta en "motivo_rechazo".

        Responde EXCLUSIVAMENTE en formato JSON:
        {{
          "valido": true,
          "nombre_pagador": "Nombre del pagador",
          "numero_verificacion": "006852001890",
          "monto_detectado": 497.69,
          "banco_detectado": "BANCO DE VENEZUELA",
          "fecha_pago": "31/07/2026",
          "motivo_rechazo": ""
        }}
        """

        if isinstance(image_input, bytes):
            image_obj = Image.open(io.BytesIO(image_input))
        else:
            image_obj = image_input

        response = self.model.generate_content([prompt, image_obj])
        raw_text = response.text.strip().replace('```json', '').replace('```', '').strip()

        try:
            return json.loads(raw_text)
        except Exception:
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {
                "valido": False,
                "nombre_pagador": "Desconocido",
                "numero_verificacion": "N/A",
                "monto_detectado": 0.0,
                "banco_detectado": "Desconocido",
                "fecha_pago": "",
                "motivo_rechazo": "No se pudo interpretar los datos del comprobante."
            }
    
    def interpretar_intencion(self, mensaje: str) -> str:
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
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def detectar_contenido_inapropiado(self, mensaje: str) -> str:
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
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def es_material_inapropiado(self, descripcion: str) -> str:
        """Determina si un material compartido es inapropiado"""
        prompt = f"""
        Determina si el siguiente contenido es apropiado para un grupo 
        universitario educativo. Considera inapropiado: contenido sexual, 
        violento, spam, o no relacionado con educación.
        
        Contenido: {descripcion}
        
        Responde SOLO "APROPIADO" o "INAPROPIADO".
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def responder_conversacion(self, mensaje: str, contexto: str = "") -> str:
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
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def extraer_datos_recaudacion(self, mensaje: str, datos_actuales: dict) -> str:
        """Extrae los campos de recaudación desde el mensaje del profesor"""
        import json
        prompt = f"""
        Analiza el siguiente mensaje y extrae información de recaudación.
        Mensaje del profesor: "{mensaje}"
        Datos que ya tenemos: {json.dumps(datos_actuales, ensure_ascii=False)}
        Identifica: concepto, monto, banco, cedula, telefono, fecha_limite.
        Responde EXCLUSIVAMENTE en JSON:
        {{"concepto": "...", "monto": 0, "banco": "...", "cedula": "...", "telefono": "...", "fecha_limite": "..."}}
        Si un campo no aparece, usa "no_encontrado".
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

