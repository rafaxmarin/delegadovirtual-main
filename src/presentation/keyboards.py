from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Estado de grupos", callback_data="menu_estado_grupos"),
            InlineKeyboardButton("💰 Recaudación", callback_data="menu_recaudacion")
        ],
        [
            InlineKeyboardButton("📢 Emitir anuncio", callback_data="menu_anuncio"),
            InlineKeyboardButton("📝 Redactar minuta", callback_data="menu_minuta")
        ],
        [
            InlineKeyboardButton("📚 Compartir material", callback_data="menu_material"),
            InlineKeyboardButton("📬 Buzón de asesoría", callback_data="menu_asesoria")
        ],
        [
            InlineKeyboardButton("⚡ Control de strikes", callback_data="menu_strikes"),
            InlineKeyboardButton("📜 Fijar reglamento", callback_data="menu_reglamento")
        ],
        [
            InlineKeyboardButton("➕ Agregar alumno", callback_data="menu_agregar"),
            InlineKeyboardButton("➖ Eliminar alumno", callback_data="menu_eliminar")
        ],
        [
            InlineKeyboardButton("❌ Cerrar panel", callback_data="menu_cerrar")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_auth_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✅ Sí, soy profesor", callback_data="soy_profesor")],
        [InlineKeyboardButton("❌ No, no soy profesor", callback_data="no_profesor")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard(callback_data: str = "volver_menu") -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def get_grupos_list_keyboard(grupos: list) -> InlineKeyboardMarkup:
    keyboard = []
    for chat_id, nombre in grupos:
        keyboard.append([InlineKeyboardButton(f"📚 {nombre}", callback_data=f"detalle_grupo_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_grupo_detalle_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔙 Volver a la lista de grupos", callback_data="menu_estado_grupos")],
        [InlineKeyboardButton("🏠 Volver al menú principal", callback_data="volver_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
