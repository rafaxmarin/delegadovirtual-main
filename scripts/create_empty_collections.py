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

def inicializar_colecciones_vacias():
    print("🔥 Inicializando y creando las 8 colecciones vacías en Firebase Cloud Firestore...\n")
    repo = FirebaseRepository(
        credentials_path=Config.FIREBASE_CREDENTIALS_PATH,
        credentials_json=Config.FIREBASE_CREDENTIALS_JSON
    )
    db = repo.db
    
    colecciones = [
        'profesores',
        'grupos',
        'recaudaciones',
        'pagos',
        'strikes',
        'asesorias',
        'asesorias_limite',
        'configuracion'
    ]

    for col in colecciones:
        doc_ref = db.collection(col).document('_schema')
        doc_ref.set({
            '_descripcion': f'Colección {col} vacía e inicializada',
            '_estado': 'activa'
        })
        print(f"  ✅ Colección '{col}' creada e inicializada en Firebase.")

    # Guardar configuración inicial predeterminada
    db.collection('configuracion').document('ACTIVE_AI_PROVIDER').set({'clave': 'ACTIVE_AI_PROVIDER', 'valor': 'gemini'})
    db.collection('configuracion').document('GEMINI_MODEL').set({'clave': 'GEMINI_MODEL', 'valor': 'gemini-flash-latest'})
    db.collection('configuracion').document('DEEPSEEK_MODEL').set({'clave': 'DEEPSEEK_MODEL', 'valor': 'deepseek-chat'})

    print("\n🎉 ¡TODAS LAS COLECCIONES HAN SIDO CREADAS Y VISIBLES EN TU CONSOLA DE FIREBASE!")

if __name__ == '__main__':
    inicializar_colecciones_vacias()
