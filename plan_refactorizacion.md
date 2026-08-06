# Plan de Refactorización e Implementación - Delegado Virtual

Este documento describe el plan detallado para refactorizar la base de código de **Delegado Virtual** hacia una **Arquitectura Limpia (Clean Architecture)**. Esta refactorización solucionará los 9 errores críticos detectados, garantizará la mantenibilidad del proyecto y facilitará futuras extensiones.

---

## Estructura Objetivo de Archivos

Reorganizaremos la raíz del proyecto creando un paquete estructurado `src/`:

```text
e:/DelegadoVirtual-main/
├── src/
│   ├── __init__.py
│   ├── config.py                     # Validación de variables de entorno con dotenv
│   ├── domain/                       # Capa 1: Modelos y Excepciones de Dominio
│   │   ├── __init__.py
│   │   ├── models.py                 # Dataclasses puros (Profesor, Grupo, Recaudacion, Strike, Asesoria)
│   │   └── exceptions.py             # Excepciones de negocio
│   ├── application/                  # Capa 2: Servicios de Negocio e Interfaces
│   │   ├── __init__.py
│   │   ├── interfaces.py             # Abstracciones para Repositorios e IA
│   │   ├── auth_service.py           # Verificación y autenticación de profesores
│   │   ├── grupo_service.py          # Registro y estado de grupos
│   │   ├── recaudacion_service.py    # Procesamiento flexible de cobros
│   │   ├── alumno_service.py         # Gestión de alumnos e invitaciones
│   │   ├── strike_service.py         # Moderación con IA y sanciones
│   │   ├── asesoria_service.py       # Buzón de preguntas y recordatorios
│   │   └── minuta_service.py         # Redacción APA y coordinación de reportes
│   ├── infrastructure/               # Capa 3: Adaptadores de Infraestructura
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   └── sqlite_repository.py  # Repositorio SQLite (sin errores de SQL o indentación)
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── gemini_adapter.py     # Adaptador de Gemini (soporte texto e imágenes con PIL/BytesIO)
│   │   └── documents/
│   │       ├── __init__.py
│   │       ├── pdf_exporter.py       # Exportador ReportLab PDF
│   │       └── docx_exporter.py      # Exportador python-docx con Pt e Inches corregidos
│   └── presentation/                 # Capa 4: Adaptador del Bot de Telegram
│       ├── __init__.py
│       ├── keyboards.py              # Constructores de teclados Inline
│       └── handlers/                 # Controladores de Telegram por módulo
│           ├── __init__.py
│           ├── auth_handlers.py
│           ├── menu_handlers.py
│           ├── grupo_handlers.py
│           ├── recaudacion_handlers.py
│           ├── alumno_handlers.py
│           ├── strike_handlers.py
│           ├── asesoria_handlers.py
│           ├── minuta_handlers.py
│           └── natural_handlers.py
├── bot.py                            # Punto de entrada principal (Container DI & Bot App)
├── requirements.txt                  # Dependencias del proyecto
└── reporte_errores.md                # Reporte técnico de errores
```

---

## Cambios Clave y Solución de Errores

> [!IMPORTANT]
> **Cambios Estructurales y de Importación:**
> - Todos los archivos sueltos en la raíz (`alumnos.py`, `anuncios.py`, `database.py`, etc.) serán migrados y organizados dentro del directorio `src/`.
> - Se creará un punto de entrada centralizado en [bot.py](file:///e:/DelegadoVirtual-main/bot.py) que inicializará las dependencias.

> [!TIP]
> **Correcciones Automáticas de Errores:**
> La refactorización corregirá automáticamente los 9 errores encontrados (bloqueo de clave, auto-expulsión en grupos, error de Gemini Vision, métodos fuera de clase, etc.).

---

## Componentes a Implementar

### 1. Dominio y Configuración (`src/domain/`, `src/config.py`)

#### [NEW] [config.py](file:///e:/DelegadoVirtual-main/src/config.py)
- Cargar y validar variables de entorno (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `PROFESOR_PASSWORD`).

#### [NEW] [models.py](file:///e:/DelegadoVirtual-main/src/domain/models.py)
- Definir dataclasses para `Profesor`, `Grupo`, `Recaudacion`, `Strike`, `Asesoria`, `Minuta`.

---

### 2. Infraestructura (`src/infrastructure/`)

#### [NEW] [sqlite_repository.py](file:///e:/DelegadoVirtual-main/src/infrastructure/database/sqlite_repository.py)
- Reemplaza y corrige [database.py](file:///e:/DelegadoVirtual-main/database.py).
- **Correcciones incluidas:**
  - `obtener_historial_strikes_por_nombre` re-indentado dentro de la clase.
  - Nuevos métodos: `es_grupo_registrado(chat_id)` y `obtener_todos_los_grupos()`.

#### [NEW] [gemini_adapter.py](file:///e:/DelegadoVirtual-main/src/infrastructure/ai/gemini_adapter.py)
- Reemplaza y mejora [gemini_handler.py](file:///e:/DelegadoVirtual-main/gemini_handler.py).
- **Corrección incluida:**
  - Conversión del archivo de Telegram a `PIL.Image` o `bytes` antes de llamar a `generate_content`.

#### [NEW] [docx_exporter.py](file:///e:/DelegadoVirtual-main/src/infrastructure/documents/docx_exporter.py)
- Reemplaza la lógica de Word de [minuta.py](file:///e:/DelegadoVirtual-main/minuta.py).
- **Corrección incluida:**
  - Asignación de unidades con `Pt(12)` e `Inches(0.5)`.

---

### 3. Capa de Aplicación (`src/application/`)

#### [NEW] [auth_service.py](file:///e:/DelegadoVirtual-main/src/application/auth_service.py)
- Lógica pura de validación de contraseñas y estado de profesores.

#### [NEW] [grupo_service.py](file:///e:/DelegadoVirtual-main/src/application/grupo_service.py)
- Lógica de registro y desvinculación de grupos.

#### [NEW] [strike_service.py](file:///e:/DelegadoVirtual-main/src/application/strike_service.py)
- Lógica de moderación de contenido y conteo de faltas.

#### [NEW] [asesoria_service.py](file:///e:/DelegadoVirtual-main/src/application/asesoria_service.py)
- Gestión del buzón de preguntas y respuestas.

---

### 4. Presentación / Telegram Handlers (`src/presentation/`)

#### [NEW] [keyboards.py](file:///e:/DelegadoVirtual-main/src/presentation/keyboards.py)
- Constructores de teclados Inline unificados.

#### [NEW] [auth_handlers.py](file:///e:/DelegadoVirtual-main/src/presentation/handlers/auth_handlers.py)
- Handlers para `/start`, botón *"Soy profesor"* y verificación de clave.

#### [NEW] [grupo_handlers.py](file:///e:/DelegadoVirtual-main/src/presentation/handlers/grupo_handlers.py)
- **Corrección incluida:** Valida que el evento `NEW_CHAT_MEMBERS` corresponda exclusivamente a la adición del bot (`user.id == context.bot.id`).

#### [NEW] [alumno_handlers.py](file:///e:/DelegadoVirtual-main/src/presentation/handlers/alumno_handlers.py)
- **Corrección incluida:** Separa limpia y correctamente `recibir_datos_alumno` y `recibir_datos_eliminar`.

#### [NEW] [strike_handlers.py](file:///e:/DelegadoVirtual-main/src/presentation/handlers/strike_handlers.py)
- **Corrección incluida:** Uso de `ChatPermissions` en lugar de diccionarios planos.

#### [NEW] [natural_handlers.py](file:///e:/DelegadoVirtual-main/src/presentation/handlers/natural_handlers.py)
- **Corrección incluida:** Revisa `esperando_password` antes de descartar a usuarios no verificados.

---

### 5. Punto de Entrada Principal

#### [MODIFY] [bot.py](file:///e:/DelegadoVirtual-main/bot.py)
- Punto de entrada limpio que inicializa la configuración, la base de datos, los servicios y registra los handlers desde `src/presentation/handlers/`.

---

## Plan de Verificación

### Pruebas Manuales
1. **Prueba de Autenticación:** Probar `/start`, seleccionar *"Soy profesor"*, ingresar la contraseña y verificar que la cuenta pase a verificado sin ignorar el mensaje.
2. **Prueba de Inclusión en Grupos:** Agregar el bot a un grupo y verificar que **NO** se auto-expulse al ingresar nuevos miembros de prueba.
3. **Prueba de Moderación y Strikes:** Enviar un mensaje de prueba con palabra moderada en un grupo registrado y verificar la asignación del strike.
4. **Prueba de Generación de Minutas:** Redactar una minuta de prueba y exportar a Word/PDF verificando que el archivo no esté dañado y que las dimensiones sean las correctas.
5. **Prueba de OCR de Comprobantes:** Probar el procesamiento de imagen con Gemini Vision asegurando que la carga no lance `TypeError`.
