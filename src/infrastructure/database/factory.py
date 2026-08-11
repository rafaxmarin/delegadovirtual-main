from src.config import Config
from src.infrastructure.database.sqlite_repository import SQLiteRepository

def get_repository():
    db_type = getattr(Config, 'DB_TYPE', 'sqlite').lower()
    if db_type == 'firebase':
        try:
            from src.infrastructure.database.firebase_repository import FirebaseRepository
            print("🔥 Inicializando repositorio de base de datos Firebase Cloud Firestore...")
            return FirebaseRepository(
                credentials_path=Config.FIREBASE_CREDENTIALS_PATH,
                credentials_json=Config.FIREBASE_CREDENTIALS_JSON
            )
        except Exception as e:
            print(f"⚠️ Error al inicializar Firebase ({e}). Se usará SQLite como fallback.")
            return SQLiteRepository(Config.DATABASE_PATH)
    else:
        print("💾 Inicializando repositorio de base de datos SQLite...")
        return SQLiteRepository(Config.DATABASE_PATH)
