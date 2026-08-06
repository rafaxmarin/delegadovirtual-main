# Reporte Técnico de Errores Encontrados - Delegado Virtual

Este documento contiene el diagnóstico detallado de los errores y fallos de lógica identificados durante la revisión del código fuente del repositorio **Delegado Virtual**.

---

## Resumen de Hallazgos

| # | Categoria | Descripción Breve | Severidad | Archivo Principal |
|---|---|---|---|---|
| 1 | Importación | Módulos importados desde paquete `handlers` inexistente | 🔴 Crítico | [bot.py](file:///e:/DelegadoVirtual-main/bot.py#L7-L18) / [natural.py](file:///e:/DelegadoVirtual-main/natural.py#L24-L67) |
| 2 | Flujo / Auth | Retorno silencioso en privado bloquea verificación de contraseña | 🔴 Crítico | [natural.py](file:///e:/DelegadoVirtual-main/natural.py#L11-L12) |
| 3 | Lógica de Bot | Bot se auto-expulsa cuando entra cualquier estudiante nuevo | 🔴 Crítico | [grupos.py](file:///e:/DelegadoVirtual-main/grupos.py#L49-L68) |
| 4 | Duplicación | Código de agregar alumnos está vacío y sobrescrito | 🔴 Crítico | [alumnos.py](file:///e:/DelegadoVirtual-main/alumnos.py#L24-L56) |
| 5 | Sintaxis / DB | Función `obtener_historial_strikes_por_nombre` fuera de la clase | 🔴 Crítico | [database.py](file:///e:/DelegadoVirtual-main/database.py#L243-L249) |
| 6 | Consulta SQL | `obtener_grupos_profesor(None)` anula monitoreo de strikes y asesorías | 🔴 Crítico | [strikes.py](file:///e:/DelegadoVirtual-main/strikes.py#L176) / [asesoria.py](file:///e:/DelegadoVirtual-main/asesoria.py#L198) |
| 7 | Telegram API | Uso de `dict` en lugar de `ChatPermissions` en `restrict_chat_member` | 🟠 Alto | [strikes.py](file:///e:/DelegadoVirtual-main/strikes.py#L234-L244) |
| 8 | Integración IA | Objeto Telegram `PhotoSize` enviado directamente a Gemini Vision | 🟠 Alto | [gemini_handler.py](file:///e:/DelegadoVirtual-main/gemini_handler.py#L80) |
| 9 | Formato Docx | Asignación de enteros raw a propiedades de unidades en `python-docx` | 🟡 Medio | [minuta.py](file:///e:/DelegadoVirtual-main/minuta.py#L218-L220) |

---

## Detalle Técnico de los Errores

### 1. Error de Importación (`ModuleNotFoundError`)
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Impide el arranque del bot)

* **Ubicación:** [bot.py:L7-L18](file:///e:/DelegadoVirtual-main/bot.py#L7-L18) y [natural.py:L24-L67](file:///e:/DelegadoVirtual-main/natural.py#L24-L67)
* **Descripción:** Los archivos intentan realizar importaciones utilizando el prefijo `from handlers.xxxx import yyyy`.
* **Causa Raíz:** Todos los archivos `.py` se encuentran sueltos en el directorio raíz. La carpeta `handlers/` no existe en la estructura del proyecto.
* **Impacto:** Ejecutar `python bot.py` finaliza inmediatamente con un error de ejecución:
  ```text
  ModuleNotFoundError: No module named 'handlers'
  ```
* **Solución Recomendada:** Cambiar las sentencias de importación a módulos locales directos (ej. `from auth import start`) o reestructurar el código en una carpeta de paquete `handlers/` o `src/presentation/handlers/`.

---

### 2. Bloqueo Total del Flujo de Autenticación de Profesores
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Impide autenticar a cualquier usuario)

* **Ubicación:** [natural.py:L11-L12](file:///e:/DelegadoVirtual-main/natural.py#L11-L12) en interacción con [auth.py:L62](file:///e:/DelegadoVirtual-main/auth.py#L62)
* **Descripción:** Toda la mensajería privada pasa por la función `procesar_mensaje_natural`.
* **Causa Raíz:** Al inicio de `procesar_mensaje_natural`, se evalúa:
  ```python
  if not db.es_profesor_verificado(user.id):
      return
  ```
  Cuando un profesor hace clic en el botón *"Soy profesor"*, el bot establece `context.user_data['esperando_password'] = True`. Cuando el profesor envía la contraseña por mensaje privado, `es_profesor_verificado` retorna `False`, provocando que la función termine inmediatamente sin llamar a `verificar_password`.
* **Impacto:** Ningún usuario puede completar la autenticación. El bot ignora cualquier contraseña ingresada.
* **Solución Recomendada:** Validar si el usuario está en el estado `esperando_password` antes de descartar el mensaje por falta de verificación.

---

### 3. Expulsión Automática del Bot cuando Entra un Estudiante al Grupo
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Provoca comportamiento errático en Telegram)

* **Ubicación:** [grupos.py:L49-L68](file:///e:/DelegadoVirtual-main/grupos.py#L49-L68)
* **Descripción:** El handler `detectar_agregacion_grupo` responde a `StatusUpdate.NEW_CHAT_MEMBERS`.
* **Causa Raíz:** La función no comprueba si el miembro añadido es el bot. Cuando un estudiante se une al grupo, `update.effective_user` pasa a ser el estudiante. La función evalúa si el estudiante es un profesor verificado (`db.es_profesor_verificado(user.id)`), y al ser falso, envía un mensaje indicando que el bot es exclusivo de profesores y ejecuta `context.bot.leave_chat(chat.id)`.
* **Impacto:** El bot abandona el grupo automáticamente cada vez que entra cualquier estudiante nuevo.
* **Solución Recomendada:** Verificar que `user.id == context.bot.id` o que el bot esté entre la lista de usuarios agregados (`new_chat_members`).

---

### 4. Función de Agregar Alumnos Vacía y Código Sobrescrito
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Funcionalidad rota)

* **Ubicación:** [alumnos.py:L24-L56](file:///e:/DelegadoVirtual-main/alumnos.py#L24-L56) y [alumnos.py:L195](file:///e:/DelegadoVirtual-main/alumnos.py#L195)
* **Descripción:**
  1. `recibir_datos_alumno` ([alumnos.py:L24](file:///e:/DelegadoVirtual-main/alumnos.py#L24)) sólo contiene:
     ```python
     if not context.user_data.get('agregando_alumno'):
         return
     ```
     y finaliza sin realizar ninguna operación.
  2. La función `recibir_datos_eliminar` está **definida dos veces** (en la línea 28 y en la línea 195).
* **Causa Raíz:** En la línea 28 se definió la lógica para *agregar* alumnos bajo el nombre `recibir_datos_eliminar`. Posteriormente, en la línea 195 se vuelve a definir la función `recibir_datos_eliminar` con la lógica de *eliminar*, lo que invalida y sobrescribe la primera versión durante el análisis del archivo por el intérprete de Python.
* **Impacto:** Es imposible agregar alumnos al grupo mediante el menú.
* **Solución Recomendada:** Renombrar la primera definición a `recibir_datos_alumno` y restaurar su lógica de agregar.

---

### 5. Fallo de Sintaxis/Indentación en `Database` (`AttributeError`)
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Error de runtime al consultar strikes)

* **Ubicación:** [database.py:L243-L249](file:///e:/DelegadoVirtual-main/database.py#L243-L249)
* **Descripción:** La función `obtener_historial_strikes_por_nombre` fue escrita al final del archivo.
* **Causa Raíz:** La definición de la función no tiene la indentación correspondiente a la clase `Database` (se encuentra en el nivel raíz del módulo).
* **Impacto:** Al ser invocada en [strikes.py:L74](file:///e:/DelegadoVirtual-main/strikes.py#L74) mediante `db.obtener_historial_strikes_por_nombre(...)`, la aplicación lanza:
  ```text
  AttributeError: 'Database' object has no attribute 'obtener_historial_strikes_por_nombre'
  ```
* **Solución Recomendada:** Indentar adecuadamente la función dentro del bloque de la clase `Database`.

---

### 6. Desactivación del Monitoreo de Strikes y Buzón de Asesorías (`obtener_grupos_profesor(None)`)
> [!CAUTION]
> **Severidad:** 🔴 Crítico (Desactiva la moderación y el buzón)

* **Ubicación:** [strikes.py:L176](file:///e:/DelegadoVirtual-main/strikes.py#L176) y [asesoria.py:L198](file:///e:/DelegadoVirtual-main/asesoria.py#L198)
* **Descripción:** Para comprobar si el grupo actual está registrado en el sistema, ambas funciones llaman a `db.obtener_grupos_profesor(None)`.
* **Causa Raíz:** En `database.py`, la consulta SQL asociada es:
  ```sql
  SELECT chat_id, nombre FROM grupos WHERE profesor_id = ?
  ```
  Al pasar `None`, SQLite busca registros donde `profesor_id IS NULL`, devolviendo siempre una lista vacía `[]`.
* **Impacto:**
  - En `strikes.py`: `monitorear_mensajes` determina que el grupo no está registrado y retorna en la línea 180. **Nunca se evalúan obscenidades ni se aplican strikes.**
  - En `asesoria.py`: `detectar_solicitud_estudiante` retorna en la línea 214. **El bot ignora cuando un estudiante menciona al bot (`@DelegadoVirtual`)**.
* **Solución Recomendada:** Crear un método específico `db.obtener_todos_los_grupos()` o `db.es_grupo_registrado(chat_id)`.

---

### 7. Tipo Incompatible en Restricción de Miembros (Telegram API v20+)
> [!WARNING]
> **Severidad:** 🟠 Alto (Falla la sanción al llegar a 3 strikes)

* **Ubicación:** [strikes.py:L234-L244](file:///e:/DelegadoVirtual-main/strikes.py#L234-L244)
* **Descripción:** Al acumular 3 strikes, el bot intenta restringir al estudiante enviando un diccionario:
  ```python
  permisos = {
      'can_send_messages': False,
      'can_send_media_messages': False, ...
  }
  await context.bot.restrict_chat_member(chat.id, user.id, permissions=permisos, ...)
  ```
* **Causa Raíz:** En la librería `python-telegram-bot` v20+, el parámetro `permissions` exige una instancia de `telegram.ChatPermissions`.
* **Impacto:** La restricción falla arrojando `TypeError`.
* **Solución Recomendada:** Utilizar `ChatPermissions(can_send_messages=False, ...)` importándolo desde `telegram`.

---

### 8. Tipo de Objeto Inválido al Enviar Imágenes a Gemini Vision
> [!WARNING]
> **Severidad:** 🟠 Alto (Falla validación de comprobantes)

* **Ubicación:** [gemini_handler.py:L80](file:///e:/DelegadoVirtual-main/gemini_handler.py#L80)
* **Descripción:** La función `analizar_comprobante_imagen(foto)` llama directamente a `model.generate_content([prompt, foto])`.
* **Causa Raíz:** El argumento `foto` recibido corresponde al objeto `PhotoSize` de Telegram, en lugar de los bytes descargados o una imagen de la librería `PIL.Image`.
* **Impacto:** Falla la ejecución de la función de IA arrojando un error de tipo al analizar comprobantes de Pago Móvil.
* **Solución Recomendada:** Descargar el archivo de la foto mediante `context.bot.get_file(foto.file_id)`, cargarlo en memoria como `PIL.Image` o bytes y pasarlo a Gemini.

---

### 9. Asignación Incorrecta de Unidades en Documentos Word
> [!NOTE]
> **Severidad:** 🟡 Medio (Formato de documento corrupto o deformado)

* **Ubicación:** [minuta.py:L218-L220](file:///e:/DelegadoVirtual-main/minuta.py#L218-L220)
* **Descripción:** En `generar_word_apa` se asigna:
  ```python
  style.font.size = 152400
  style.paragraph_format.first_line_indent = 914400
  ```
* **Causa Raíz:** En `python-docx`, las propiedades `.size` y `.first_line_indent` deben configurarse utilizando las clases de conversión `docx.shared.Pt` y `docx.shared.Inches`.
* **Impacto:** Los documentos `.docx` generados pueden presentar fuentes excesivamente grandes o provocar advertencias de formato al abrirse en Microsoft Word.
* **Solución Recomendada:** Asignar `Pt(12)` para la fuente e `Inches(0.5)` para la sangría de primera línea.

---

## Conclusión

El bot cuenta con un diseño conceptual robusto y un abanico completo de funcionalidades. Sin embargo, los 9 errores detallados anteriormente impiden su ejecución correcta en un entorno real. 

Se recomienda proceder con el plan de **Refactorización a Clean Architecture**, el cual corregirá simultáneamente estos fallos de implementación e independizará las capas de presentación, negocio, base de datos e inteligencia artificial.
