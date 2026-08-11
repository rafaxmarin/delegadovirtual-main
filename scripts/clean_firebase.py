import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config import Config
from src.infrastructure.database.firebase_repository import FirebaseRepository

def limpiar_firebase():
    print("🔥 Vaciando y limpiando todas las colecciones en Firebase Cloud Firestore...\n")
    repo = FirebaseRepository(
        credentials_path=Config.FIREBASE_CREDENTIALS_PATH,
        credentials_json=Config.FIREBASE_CREDENTIALS_JSON
    )
    db = repo.db
    
    colecciones = ['profesores', 'grupos', 'recaudaciones', 'pagos', 'strikes', 'asesorias', 'asesorias_limite', 'configuracion']
    
    total_eliminados = 0
    for col_name in colecciones:
        docs = list(db.collection(col_name).stream())
        if docs:
            batch = db.batch()
            count_col = 0
            for d in docs:
                batch.delete(d.reference)
                count_col += 1
                total_eliminados += 1
            batch.commit()
            print(f"  🗑️ Colección '{col_name}': {count_col} documentos eliminados.")
        else:
            print(f"  ✨ Colección '{col_name}': ya está limpia (0 documentos).")
            
    print(f"\n🎉 ¡FIREBASE LIMPIO! Se han eliminado {total_eliminados} documentos. La base de datos está completamente vacía y lista para uso nuevo.")

if __name__ == '__main__':
    limpiar_firebase()
