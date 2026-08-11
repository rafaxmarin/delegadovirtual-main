import os
import sys
import sqlite3

# Añadir el directorio raíz al PATH para poder importar los módulos de src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config
from src.infrastructure.database.firebase_repository import FirebaseRepository

def migrar_sqlite_a_firebase(db_sqlite_path: str = 'delegado_virtual.db'):
    if not os.path.exists(db_sqlite_path):
        print(f"❌ Error: No se encontró la base de datos SQLite en: '{db_sqlite_path}'")
        return

    print(f"📦 Leyendo base de datos SQLite desde: {db_sqlite_path}...")
    conn = sqlite3.connect(db_sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("🔥 Conectando a Firebase Cloud Firestore...")
    try:
        fb_repo = FirebaseRepository(
            credentials_path=Config.FIREBASE_CREDENTIALS_PATH,
            credentials_json=Config.FIREBASE_CREDENTIALS_JSON
        )
    except Exception as e:
        print(f"❌ Error al conectar con Firebase: {e}")
        print("Asegúrate de haber configurado tu archivo .env con FIREBASE_CREDENTIALS_PATH o FIREBASE_CREDENTIALS_JSON")
        return

    db = fb_repo.db
    total_migrados = 0

    # 1. Tabla PROFESORES
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profesores'")
    if cursor.fetchone():
        profesores = cursor.execute("SELECT * FROM profesores").fetchall()
        print(f"➡️ Migrando {len(profesores)} profesores...")
        batch = db.batch()
        for p in profesores:
            ref = db.collection('profesores').document(str(p['user_id']))
            batch.set(ref, {
                'user_id': int(p['user_id']),
                'username': p['username'] or '',
                'verificado': int(p['verificado'] or 0),
                'fecha_registro': p['fecha_registro'] or ''
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Profesores migrados exitosamente.")

    # 2. Tabla GRUPOS
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grupos'")
    if cursor.fetchone():
        grupos = cursor.execute("SELECT * FROM grupos").fetchall()
        print(f"➡️ Migrando {len(grupos)} grupos...")
        batch = db.batch()
        for g in grupos:
            ref = db.collection('grupos').document(str(g['chat_id']))
            batch.set(ref, {
                'chat_id': int(g['chat_id']),
                'nombre': g['nombre'] or '',
                'profesor_id': int(g['profesor_id']) if g['profesor_id'] is not None else None,
                'fecha_registro': g['fecha_registro'] or ''
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Grupos migrados exitosamente.")

    # 3. Tabla RECAUDACIONES
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recaudaciones'")
    if cursor.fetchone():
        recaudaciones = cursor.execute("SELECT * FROM recaudaciones").fetchall()
        print(f"➡️ Migrando {len(recaudaciones)} recaudaciones...")
        batch = db.batch()
        for r in recaudaciones:
            ref = db.collection('recaudaciones').document(str(r['id']))
            batch.set(ref, {
                'id': int(r['id']),
                'profesor_id': int(r['profesor_id']) if r['profesor_id'] is not None else None,
                'grupo_id': int(r['grupo_id']) if r['grupo_id'] is not None else None,
                'concepto': r['concepto'] or '',
                'monto': float(r['monto'] or 0.0),
                'banco': r['banco'] or '',
                'cedula': r['cedula'] or '',
                'telefono': r['telefono'] or '',
                'fecha_limite': r['fecha_limite'] or '',
                'activa': int(r['activa'] or 0),
                'mensaje_lista_id': int(r['mensaje_lista_id']) if r['mensaje_lista_id'] is not None else None
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Recaudaciones migradas exitosamente.")

    # 4. Tabla PAGOS
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pagos'")
    if cursor.fetchone():
        pagos = cursor.execute("SELECT * FROM pagos").fetchall()
        print(f"➡️ Migrando {len(pagos)} pagos...")
        batch = db.batch()
        for p in pagos:
            ref = db.collection('pagos').document(str(p['id']))
            batch.set(ref, {
                'id': int(p['id']),
                'recaudacion_id': int(p['recaudacion_id']) if p['recaudacion_id'] is not None else None,
                'estudiante_id': int(p['estudiante_id']) if p['estudiante_id'] is not None else None,
                'estudiante_nombre': p['estudiante_nombre'] or '',
                'numero_verificacion': p['numero_verificacion'] or '',
                'fecha_pago': p['fecha_pago'] or '',
                'validado': int(p['validado'] or 1)
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Pagos migrados exitosamente.")

    # 5. Tabla STRIKES
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strikes'")
    if cursor.fetchone():
        strikes = cursor.execute("SELECT * FROM strikes").fetchall()
        print(f"➡️ Migrando {len(strikes)} strikes...")
        batch = db.batch()
        for s in strikes:
            ref = db.collection('strikes').document(str(s['id']))
            batch.set(ref, {
                'id': int(s['id']),
                'estudiante_id': int(s['estudiante_id']) if s['estudiante_id'] is not None else None,
                'estudiante_nombre': s['estudiante_nombre'] or '',
                'grupo_id': int(s['grupo_id']) if s['grupo_id'] is not None else None,
                'motivo': s['motivo'] or '',
                'fecha': s['fecha'] or ''
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Strikes migrados exitosamente.")

    # 6. Tabla ASESORIAS
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asesorias'")
    if cursor.fetchone():
        asesorias = cursor.execute("SELECT * FROM asesorias").fetchall()
        print(f"➡️ Migrando {len(asesorias)} asesorías...")
        batch = db.batch()
        for a in asesorias:
            ref = db.collection('asesorias').document(str(a['id']))
            batch.set(ref, {
                'id': int(a['id']),
                'grupo_id': int(a['grupo_id']) if a['grupo_id'] is not None else None,
                'grupo_nombre': a['grupo_nombre'] or '',
                'estudiante_nombre': a['estudiante_nombre'] or '',
                'pregunta': a['pregunta'] or '',
                'fecha': a['fecha'] or '',
                'respondida': int(a['respondida'] or 0)
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Asesorías migradas exitosamente.")

    # 7. Tabla ASESORIAS_LIMITE
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asesorias_limite'")
    if cursor.fetchone():
        limites = cursor.execute("SELECT * FROM asesorias_limite").fetchall()
        print(f"➡️ Migrando {len(limites)} límites de asesoría...")
        batch = db.batch()
        for al in limites:
            doc_id = f"{al['grupo_id']}_{al['fecha']}"
            ref = db.collection('asesorias_limite').document(doc_id)
            batch.set(ref, {
                'grupo_id': int(al['grupo_id']),
                'fecha': al['fecha'],
                'contador': int(al['contador'] or 0)
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Límites de asesoría migrados exitosamente.")

    # 8. Tabla CONFIGURACION
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracion'")
    if cursor.fetchone():
        configs = cursor.execute("SELECT * FROM configuracion").fetchall()
        print(f"➡️ Migrando {len(configs)} configuraciones...")
        batch = db.batch()
        for c in configs:
            ref = db.collection('configuracion').document(c['clave'])
            batch.set(ref, {
                'clave': c['clave'],
                'valor': c['valor'] or ''
            })
            total_migrados += 1
        batch.commit()
        print("  ✅ Configuraciones migradas exitosamente.")

    conn.close()
    print(f"\n🎉 ¡MIGRACIÓN COMPLETADA! Se han copiado {total_migrados} registros a Firebase Firestore.")

if __name__ == '__main__':
    migrar_sqlite_a_firebase()
