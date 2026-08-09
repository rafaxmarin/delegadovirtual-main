# Aislamiento Multiusuario Seguro entre Profesores

Cerrar las brechas de seguridad que permiten que un profesor potencialmente acceda a grupos de otro profesor, hardening general del sistema multiusuario, y nueva funcionalidad de desvinculación de grupos.

## Diagnóstico Actual

Se auditaron **todos** los handlers del bot. El resultado:

| Handler | Archivo | Lista grupos ✅ | Valida pertenencia al actuar 🔴 |
|---|---|---|---|
| `enviar_anuncio_grupo` | `anuncio_handlers.py:101` | ✅ | 🔴 No valida |
| `enviar_recaudacion` | `recaudacion_handlers.py:134` | ✅ | 🔴 No valida |
| `enviar_material` | `material_handlers.py:126` | ✅ | 🔴 No valida |
| `despachar_minuta` | `minuta_handlers.py:109` | ✅ | 🔴 No valida |
| `fijar_reglamento_grupo` | `reglamento_handlers.py:91` | ✅ | 🔴 No valida (rama `else`) |
| `invitar_alumno_grupo` | `alumno_handlers.py:53` | ✅ | 🔴 No valida |
| `listar_estudiantes_grupo` | `alumno_handlers.py:143` | ✅ | 🔴 No valida |
| `confirmar_eliminar_alumno` | `alumno_handlers.py:206` | ✅ | 🔴 No valida |
| `detalle_grupo` | `grupo_handlers.py:41` | ✅ | 🔴 No valida |
| `ver_historial_strikes` | `strike_handlers.py:58` | ✅ | 🔴 No valida |
| `ignorar_asesoria` | `asesoria_handlers.py:137` | ✅ | 🔴 No valida |
| `enviar_recordatorio_asesoria` | `asesoria_handlers.py:285` | N/A | 🔴 Usa `obtener_todos_los_grupos` |

Además, **no existe funcionalidad** para que el profesor desvincule un grupo ya registrado.

---

## Propuesta de Cambios

---

### Componente 1: Repositorio (Capa de datos)

#### [MODIFY] sqlite_repository.py (`src/infrastructure/database/sqlite_repository.py`)

1. **Nuevo método `es_grupo_de_profesor(chat_id, profesor_id) -> bool`**: Consulta rápida que valida si un grupo pertenece a un profesor específico. Será la pieza central de toda la validación.

2. **Eliminar el fallback peligroso** en `obtener_grupos_profesor`: Cuando `profesor_id` es `None`, actualmente retorna todos los grupos. Se eliminará esa rama — si `profesor_id` es `None`, retornará lista vacía.

3. **Deprecar `obtener_todos_los_grupos`**: No eliminarlo aún (se usa en el recordatorio de asesorías), pero documentarlo como uso interno limitado.

---

### Componente 2: Interfaz del repositorio

#### [MODIFY] interfaces.py (`src/application/interfaces.py`)

Agregar `es_grupo_de_profesor(chat_id: int, profesor_id: int) -> bool` al protocolo `RepositoryInterface`.

---

### Componente 3: Función auxiliar de validación

#### [NEW] auth_utils.py (`src/presentation/auth_utils.py`)

Función auxiliar reutilizable:

```python
async def verificar_pertenencia_grupo(
    chat_id: int,
    user_id: int,
    db,
    query  # CallbackQuery para responder con error
) -> bool:
    """Verifica que el grupo pertenezca al profesor. 
    Si no, responde con error y retorna False."""
    if not db.es_grupo_de_profesor(chat_id, user_id):
        await query.edit_message_text(
            "❌ No tienes permisos sobre este grupo."
        )
        return False
    return True
```

---

### Componente 4: Aplicar validación en todos los handlers de acción

Se agrega una llamada a `verificar_pertenencia_grupo()` al inicio de cada handler que recibe un `chat_id` vía callback. El patrón es siempre el mismo:

```python
if not await verificar_pertenencia_grupo(chat_id, query.from_user.id, db, query):
    return
```

Los archivos a modificar:

#### [MODIFY] anuncio_handlers.py (`src/presentation/handlers/anuncio_handlers.py`)
- `enviar_anuncio_grupo` (línea 101): Agregar validación antes de enviar al grupo.

#### [MODIFY] recaudacion_handlers.py (`src/presentation/handlers/recaudacion_handlers.py`)
- `enviar_recaudacion` (línea 134): Agregar validación antes de enviar al grupo.

#### [MODIFY] material_handlers.py (`src/presentation/handlers/material_handlers.py`)
- `enviar_material` (línea 126): Agregar validación antes de enviar al grupo.

#### [MODIFY] minuta_handlers.py (`src/presentation/handlers/minuta_handlers.py`)
- `despachar_minuta` (línea 109): Agregar validación antes de enviar al grupo.

#### [MODIFY] reglamento_handlers.py (`src/presentation/handlers/reglamento_handlers.py`)
- `fijar_reglamento_grupo` (línea 91): Agregar validación en la rama `else` (grupo individual).

#### [MODIFY] alumno_handlers.py (`src/presentation/handlers/alumno_handlers.py`)
- `invitar_alumno_grupo` (línea 53): Agregar validación.
- `listar_estudiantes_grupo` (línea 143): Agregar validación.
- `confirmar_eliminar_alumno` (línea 206): Agregar validación.

#### [MODIFY] grupo_handlers.py (`src/presentation/handlers/grupo_handlers.py`)
- `detalle_grupo` (línea 41): Agregar validación.

#### [MODIFY] strike_handlers.py (`src/presentation/handlers/strike_handlers.py`)
- `ver_historial_strikes` (línea 58): Agregar validación usando `obtener_profesor_de_grupo`.

#### [MODIFY] asesoria_handlers.py (`src/presentation/handlers/asesoria_handlers.py`)
- `ignorar_asesoria` (línea 137): Agregar validación de que la asesoría pertenezca al profesor.

---

### Componente 5: Funcionalidad de desvincular grupo

> **IMPORTANTE:** Funcionalidad nueva. Permite al profesor desconectar un grupo desde la pantalla de detalle.

#### [MODIFY] grupo_handlers.py (`src/presentation/handlers/grupo_handlers.py`)

**Nuevas funciones:**

1. **`confirmar_desvincular_grupo`** — Se activa con callback `desvincular_grupo_{chat_id}`. Muestra un mensaje de confirmación con dos botones:
   - "✅ Sí, desvincular" → `confirmar_desvincular_{chat_id}`
   - "❌ Cancelar" → `menu_estado_grupos`

2. **`ejecutar_desvincular_grupo`** — Se activa con callback `confirmar_desvincular_{chat_id}`. Ejecuta:
   - Validar pertenencia del grupo al profesor (usando `verificar_pertenencia_grupo`).
   - Llamar a `db.eliminar_grupo(chat_id)` para borrar el registro de la BD.
   - Llamar a `context.bot.leave_chat(chat_id)` para que el bot abandone el grupo de Telegram.
   - Enviar mensaje de despedida al grupo antes de salir: "🤖 El Delegado Virtual ha sido desvinculado de este grupo por el profesor."
   - Confirmar al profesor: "✅ Grupo desvinculado exitosamente."

#### [MODIFY] keyboards.py (`src/presentation/keyboards.py`)

Modificar `get_grupo_detalle_keyboard` para aceptar un parámetro `chat_id` y agregar el botón de desvincular:

```python
def get_grupo_detalle_keyboard(chat_id: int = None) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔙 Volver a la lista", callback_data="menu_estado_grupos")],
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="volver_menu")]
    ]
    if chat_id:
        keyboard.insert(0, [
            InlineKeyboardButton("🔗 Desvincular grupo", callback_data=f"desvincular_grupo_{chat_id}")
        ])
    return InlineKeyboardMarkup(keyboard)
```

#### [MODIFY] bot.py (`bot.py`)

Registrar los nuevos callbacks:

```python
application.add_handler(CallbackQueryHandler(confirmar_desvincular_grupo, pattern='^desvincular_grupo_'))
application.add_handler(CallbackQueryHandler(ejecutar_desvincular_grupo, pattern='^confirmar_desvincular_'))
```

Actualizar el import de `grupo_handlers` para incluir las nuevas funciones.

---

### Flujo visual de desvinculación

```
📊 Estado de grupos
    ↓
Selecciona un grupo
    ↓
📊 Detalle del grupo (Nombre, Estudiantes, ID)
    ↓
🔗 Desvincular grupo
    ↓
⚠️ ¿Estás seguro? Se eliminará el registro y el bot saldrá del grupo
    ↓                          ↓
✅ Sí                       ❌ No → Vuelve al detalle
    ↓
Bot envía despedida al grupo
    ↓
Bot sale del grupo (leave_chat)
    ↓
Se elimina registro de BD
    ↓
✅ Grupo desvinculado
```

---

## Resumen de archivos tocados

| Archivo | Tipo de cambio |
|---|---|
| `sqlite_repository.py` | Nuevo método + eliminar fallback |
| `interfaces.py` | Agregar método al protocolo |
| `auth_utils.py` | **[NEW]** Función auxiliar centralizada |
| `anuncio_handlers.py` | +1 validación |
| `recaudacion_handlers.py` | +1 validación |
| `material_handlers.py` | +1 validación |
| `minuta_handlers.py` | +1 validación |
| `reglamento_handlers.py` | +1 validación |
| `alumno_handlers.py` | +3 validaciones |
| `grupo_handlers.py` | +1 validación + 2 funciones nuevas (desvincular) |
| `strike_handlers.py` | +1 validación |
| `asesoria_handlers.py` | +1 validación |
| `keyboards.py` | Modificar `get_grupo_detalle_keyboard` |
| `bot.py` | Registrar 2 nuevos callbacks + actualizar import |

**Total: 14 archivos, 1 nuevo, 13 modificados.**

## Verificación

### Pruebas manuales
1. Registrar dos profesores de prueba con dos cuentas de Telegram distintas.
2. Cada profesor registra un grupo diferente.
3. Verificar que el Profesor A no pueda ver/actuar sobre los grupos del Profesor B en ninguno de los flujos (anuncios, recaudaciones, material, minutas, reglamento, alumnos, strikes, asesorías).
4. Probar el flujo completo de desvinculación:
   - Ir a Estado de grupos → seleccionar grupo → Desvincular → Confirmar.
   - Verificar que el bot sale del grupo de Telegram.
   - Verificar que el grupo ya no aparece en la lista del profesor.
5. Verificar que el bot sigue funcionando normalmente para un solo profesor.

### Verificación de código
- Ejecutar el bot con `python bot.py` y confirmar que arranca sin errores de importación.
- Revisar que no haya regresiones en los flujos existentes.
