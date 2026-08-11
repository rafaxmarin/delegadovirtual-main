import requests
import json
from typing import Union, Any
from src.config import Config

class DeepSeekAdapter:
    BASE_URL = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or Config.DEEPSEEK_API_KEY
        self.model_name = model_name or getattr(Config, 'DEEPSEEK_MODEL', 'deepseek-chat')

    @classmethod
    def probar_conexion(cls, api_key: str, model_name: str = None) -> tuple[bool, str]:
        """Realiza una consulta de prueba a la API de DeepSeek"""
        if not api_key:
            return False, "No se ha proporcionado clave API para DeepSeek."
        
        target_model = model_name or getattr(Config, 'DEEPSEEK_MODEL', 'deepseek-chat')
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": "Eres un asistente de prueba."},
                {"role": "user", "content": "Responde únicamente con la palabra 'OK'"}
            ],
            "stream": False
        }

        try:
            response = requests.post(cls.BASE_URL, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                return True, content
            else:
                return False, f"DeepSeek respondió con error HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def _generar_respuesta(self, prompt: str, system_prompt: str = "Eres un asistente universitario atento y profesional.") -> str:
        if not self.api_key:
            raise ValueError("No se ha configurado la clave API de DeepSeek.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }

        response = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()

    def estructurar_texto_formal(self, texto: str) -> str:
        prompt = f"Convierte el siguiente mensaje informal en un anuncio formal, claro y respetuoso para un entorno universitario:\n\n{texto}\n\nSolo responde con el texto formateado final, sin notas ni comillas."
        return self._generar_respuesta(prompt)

    def transcribir_y_estructurar(self, texto_o_transcripcion: str) -> str:
        prompt = f"Estructura y corrige formalmente el siguiente texto para un entorno universitario:\n\n{texto_o_transcripcion}\n\nSolo responde con el texto pulido."
        return self._generar_respuesta(prompt)

    def generar_minuta_apa(self, contenido: str, formato: str) -> str:
        prompt = f"Redacta una minuta académica en normas APA 7ma edición. Formato solicitado: {formato}.\nContenido: {contenido}\n\nIncluye título, introducción, desarrollo, conclusión y referencias si aplica."
        return self._generar_respuesta(prompt)

    def generar_mensaje_introductorio(self, material_descripcion: str) -> str:
        prompt = f"Crea un breve mensaje introductorio (2-3 líneas) para presentar este material a estudiantes universitarios:\n{material_descripcion}\n\nSolo responde con el mensaje."
        return self._generar_respuesta(prompt)

    def interpretar_intencion(self, mensaje: str) -> str:
        prompt = f"""
        Analiza el siguiente mensaje de un profesor y determina cuál de las opciones (1-10) requiere:
        1. estado_grupos
        2. recaudacion
        3. emitir_anuncio
        4. redactar_minuta
        5. compartir_material
        6. buzon_asesoria
        7. control_strikes
        8. fijar_reglamento
        9. agregar_alumno
        10. eliminar_alumno
        
        Mensaje: {mensaje}
        Responde SOLO con el número (1-10) o 0 si no estás seguro.
        """
        return self._generar_respuesta(prompt)

    def detectar_contenido_inapropiado(self, mensaje: str) -> str:
        prompt = f"Analiza si este mensaje tiene malas palabras, spam u ofensas: '{mensaje}'. Responde SOLO 'SI - motivo' o 'NO'."
        return self._generar_respuesta(prompt)

    def es_material_inapropiado(self, descripcion: str) -> str:
        prompt = f"¿Es el siguiente contenido inapropiado para un entorno universitario (violencia, pornografía, spam)? '{descripcion}'. Responde SOLO 'APROPIADO' o 'INAPROPIADO'."
        return self._generar_respuesta(prompt)

    def responder_conversacion(self, mensaje: str, contexto: str = "") -> str:
        prompt = f"Contexto: {contexto}\nMensaje del profesor: {mensaje}\n\nResponde como el Delegado Virtual de la UDO Monagas de manera amable y concisa."
        return self._generar_respuesta(prompt)

    def extraer_datos_recaudacion(self, mensaje: str, datos_actuales: dict) -> str:
        prompt = f"""
        Analiza el siguiente mensaje y extrae información de recaudación.
        Mensaje del profesor: "{mensaje}"
        Datos que ya tenemos: {json.dumps(datos_actuales, ensure_ascii=False)}
        Identifica: concepto, monto, banco, cedula, telefono, fecha_limite.
        Responde EXCLUSIVAMENTE en JSON:
        {{"concepto": "...", "monto": 0, "banco": "...", "cedula": "...", "telefono": "...", "fecha_limite": "..."}}
        Si un campo no aparece, usa "no_encontrado".
        """
        return self._generar_respuesta(prompt)

