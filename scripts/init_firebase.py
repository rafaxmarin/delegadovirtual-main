import json
import os
import sys
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

def main():
    print("[Firebase] Creando colecciones con documentos iniciales en Firebase Firestore...")
    
    cred = None
    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

    if cred_json and cred_json.strip():
        try:
            cred = credentials.Certificate(json.loads(cred_json))
            print("Cargando credenciales desde FIREBASE_CREDENTIALS_JSON")
        except Exception as e:
            print(f"Error al leer JSON: {e}")

    if not cred and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            print(f"Cargando credenciales desde {cred_path}")
        except Exception as e:
            print(f"Error al leer {cred_path}: {e}")

    if not cred:
        print("ERROR: No se encontraron credenciales de Firebase válidas.")
        sys.exit(1)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    colecciones = {
        'profesores': 'Registro de profesores verificados',
        'grupos': 'Grupos académicos vinculados al bot',
        'recaudaciones': 'Recaudaciones activas e históricas',
        'pagos': 'Pagos validados por comprobante o efectivo',
        'strikes': 'Strikes e infracciones de estudiantes',
        'asesorias': 'Consultas y preguntas al profesor',
        'asesorias_limite': 'Límite diario de preguntas por grupo',
        'configuracion': 'Configuración de modelos e IA',
        'estudiantes_grupo': 'Lista oficial de estudiantes por grupo (Excel)',
        'miembros_telegram': 'Registro pasivo de miembros de Telegram',
        'pendientes_verificacion': 'Ultimátum y pendientes de expulsión (12h)'
    }

    print("\nCreando documentos de esquema en cada colección:")
    for col_name, descripcion in colecciones.items():
        doc_ref = db.collection(col_name).document('_info')
        doc_ref.set({
            'descripcion': descripcion,
            'estado': 'Activa',
            'ultima_actualizacion': datetime.now().isoformat()
        })
        print(f" OK - Coleccion '{col_name}' creada y visible en la consola de Firebase.")

    print("\nTODAS LAS COLECCIONES AHORA SON VISIBLES EN LA CONSOLA DE FIREBASE FIRESTORE.")

if __name__ == '__main__':
    main()
