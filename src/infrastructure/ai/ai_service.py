from typing import Union, Any
from PIL import Image
from src.config import Config
from src.infrastructure.ai.gemini_adapter import GeminiAdapter
from src.infrastructure.ai.deepseek_adapter import DeepSeekAdapter

class AIService:
    """Servicio unificado de IA que delega solicitudes a Gemini o DeepSeek según el proveedor activo"""

    def _get_adapter(self):
        provider = getattr(Config, 'ACTIVE_AI_PROVIDER', 'gemini').lower()
        if provider == 'deepseek':
            return DeepSeekAdapter()
        return GeminiAdapter()

    def estructurar_texto_formal(self, texto: str) -> str:
        return self._get_adapter().estructurar_texto_formal(texto)

    def transcribir_y_estructurar(self, texto_o_transcripcion: str) -> str:
        return self._get_adapter().transcribir_y_estructurar(texto_o_transcripcion)

    def generar_minuta_apa(self, contenido: str, formato: str) -> str:
        return self._get_adapter().generar_minuta_apa(contenido, formato)

    def generar_mensaje_introductorio(self, material_descripcion: str) -> str:
        return self._get_adapter().generar_mensaje_introductorio(material_descripcion)

    def interpretar_intencion(self, mensaje: str) -> str:
        return self._get_adapter().interpretar_intencion(mensaje)

    def detectar_contenido_inapropiado(self, mensaje: str) -> str:
        return self._get_adapter().detectar_contenido_inapropiado(mensaje)

    def es_material_inapropiado(self, descripcion: str) -> str:
        return self._get_adapter().es_material_inapropiado(descripcion)

    def responder_conversacion(self, mensaje: str, contexto: str = "") -> str:
        return self._get_adapter().responder_conversacion(mensaje, contexto)

    def analizar_comprobante_imagen(self, image_input: Union[bytes, Image.Image]) -> str:
        # Visión: Gemini gestiona el análisis de imágenes
        return GeminiAdapter().analizar_comprobante_imagen(image_input)

    def validar_comprobante_contra_recaudacion(self, image_input: Union[bytes, Image.Image], datos_recaudacion: dict) -> dict:
        # Visión: Gemini gestiona la lectura de comprobantes bancarios
        return GeminiAdapter().validar_comprobante_contra_recaudacion(image_input, datos_recaudacion)
