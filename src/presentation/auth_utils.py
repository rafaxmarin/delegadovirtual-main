from telegram import CallbackQuery


async def verificar_pertenencia_grupo(
    chat_id: int,
    user_id: int,
    db,
    query: CallbackQuery
) -> bool:
    """Verifica que el grupo pertenezca al profesor.
    Si no, responde con error y retorna False."""
    if not db.es_grupo_de_profesor(chat_id, user_id):
        await query.edit_message_text(
            "❌ No tienes permisos sobre este grupo."
        )
        return False
    return True
