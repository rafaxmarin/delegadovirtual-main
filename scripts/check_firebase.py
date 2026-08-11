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

def verificar_firebase():
    print("🔥 Verificando contenido en Firebase Cloud Firestore...\n")
    repo = FirebaseRepository(
        credentials_path=Config.FIREBASE_CREDENTIALS_PATH,
        credentials_json=Config.FIREBASE_CREDENTIALS_JSON
    )
    db = repo.db
    
    colecciones = ['profesores', 'grupos', 'recaudaciones', 'pagos', 'strikes', 'asesorias', 'asesorias_limite', 'configuracion']
    
    total_documentos = 0
    for col_name in colecciones:
        docs = list(db.collection(col_name).stream())
        print(f"📦 Colección '{col_name}': {len(docs)} documentos")
        total_documentos += len(docs)
        for d in docs:
            print(f"   📄 ID: {d.id} -> {d.to_dict()}")
        print("-" * 50)
        
    print(f"\n✅ Verificación completada: Hay un total de {total_documentos} documentos guardados en Firebase.")

if __name__ == '__main__':
    verificar_firebase()
