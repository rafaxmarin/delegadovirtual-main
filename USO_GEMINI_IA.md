# Uso de la Inteligencia Artificial (Google Gemini) en Delegado Virtual

La variable de entorno `GEMINI_API_KEY` le otorga capacidades de Inteligencia Artificial al bot mediante el modelo **Google Gemini 2.5 Flash**. A continuación se detallan las 6 funciones principales donde se utiliza la IA dentro del sistema:

---

## 1. 📷 Visión por IA: Análisis de Comprobantes de Pago
Cuando un estudiante envía la imagen/captura de un pago móvil o transferencia bancaria en un grupo con recaudación activa:
* **Función:** `analizar_comprobante_imagen`
* **Acción:** Procesa la imagen binaria e identifica automáticamente:
  - Nombre y apellido del pagador.
  - Banco emisor y receptor.
  - Cédula de identidad.
  - Número de teléfono.
  - Fecha y hora de la transacción.
* **Beneficio:** Evita que el profesor tenga que verificar manualmente los pagos uno por uno.

---

## 2. 📄 Redacción de Minutas Académicas (APA 7ma Edición)
Cuando el profesor envía notas o borrador de una reunión o clase:
* **Función:** `generar_minuta_apa`
* **Acción:** Transforma los apuntes en una minuta formal estructurada según las normas **APA (7ª edición)**, incluyendo:
  - Título del encuentro.
  - Introducción.
  - Desarrollo de puntos tratados.
  - Conclusiones y referencias.
* **Beneficio:** Genera documentos oficiales listos para ser exportados a **PDF** y **Word (.docx)**.

---

## 3. 🛡️ Moderación de Contenido y Control de Strikes
Monitorea los mensajes enviados por los estudiantes en los grupos de clase registrados:
* **Función:** `detectar_contenido_inapropiado`
* **Acción:** Analiza el texto en busca de:
  - Malas palabras u obscenidades.
  - Lenguaje ofensivo o discriminatorio.
  - Spam o contenido no educativo.
* **Beneficio:** Otorga automáticamente faltas (*strikes*) al estudiante infractor y aplica restricciones de escritura por 24 horas al acumular 3 faltas.

---

## 4. 📢 Estructuración de Anuncios Oficiales
Cuando el profesor dicta o escribe un comunicado informal:
* **Función:** `estructurar_texto_formal`
* **Acción:** Adapta el mensaje borrador a un tono institucional, claro, respetuoso y profesional para el entorno universitario.
* **Beneficio:** Garantiza una comunicación formal en los canales de clase.

---

## 5. 🧠 Procesamiento de Lenguaje Natural (Chat Privado)
Cuando el profesor le escribe mensajes de texto al bot en lugar de usar botones:
* **Función:** `interpretar_intencion` y `responder_conversacion`
* **Acción:** Determina qué acción desea ejecutar el docente (crear cobro, fijar normas, ver estado, etc.) y extrae entidades clave (montos, fechas, bancos).
* **Beneficio:** Permite una interacción fluida en lenguaje natural.

---

## 6. 📚 Presentación Introductoria de Material de Estudio
Cuando el profesor comparte archivos PDF, documentos Word o enlaces web:
* **Función:** `generar_mensaje_introductorio`
* **Acción:** Redacta una breve síntesis introductoria motivadora (2 a 3 líneas) orientada a los estudiantes para presentar el recurso.
* **Beneficio:** Mejora la presentación del material en los grupos de Telegram.

---

## Ubicación del Adaptador en el Código

Toda la lógica de integración con la API de Google Gemini se encuentra encapsulada en la capa de infraestructura:
📌 [src/infrastructure/ai/gemini_adapter.py](file:///e:/DelegadoVirtual-main/src/infrastructure/ai/gemini_adapter.py)
