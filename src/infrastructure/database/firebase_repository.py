import json
import os
import time
from datetime import datetime
from typing import List, Tuple, Optional

import firebase_admin
from firebase_admin import credentials, firestore


class FirebaseRepository:
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[str] = None):
        if not firebase_admin._apps:
            cred = None
            if credentials_json and credentials_json.strip():
                try:
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                except Exception as e:
                    print(f"⚠️ Error al parsear FIREBASE_CREDENTIALS_JSON: {e}")
            
            if not cred and credentials_path and os.path.exists(credentials_path):
                try:
                    cred = credentials.Certificate(credentials_path)
                except Exception as e:
                    print(f"⚠️ Error al cargar FIREBASE_CREDENTIALS_PATH ({credentials_path}): {e}")
            
            if not cred:
                if os.path.exists('firebase-credentials.json'):
                    cred = credentials.Certificate('firebase-credentials.json')
                else:
                    try:
                        cred = credentials.ApplicationDefault()
                    except Exception:
                        raise ValueError(
                            "❌ No se configuraron credenciales válidas para Firebase. "
                            "Define FIREBASE_CREDENTIALS_PATH o FIREBASE_CREDENTIALS_JSON en tu archivo .env"
                        )
            
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()

    # --- PROFESORES ---
    def registrar_profesor(self, user_id: int, username: str):
        doc_ref = self.db.collection('profesores').document(str(user_id))
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set({
                'user_id': user_id,
                'username': username,
                'verificado': 0,
                'fecha_registro': datetime.now().isoformat()
            })

    def verificar_profesor(self, user_id: int):
        doc_ref = self.db.collection('profesores').document(str(user_id))
        doc_ref.update({'verificado': 1})

    def es_profesor_verificado(self, user_id: int) -> bool:
        doc = self.db.collection('profesores').document(str(user_id)).get()
        if doc.exists:
            data = doc.to_dict()
            return bool(data.get('verificado') == 1)
        return False

    # --- GRUPOS ---
    def registrar_grupo(self, chat_id: int, nombre: str, profesor_id: int):
        doc_ref = self.db.collection('grupos').document(str(chat_id))
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set({
                'chat_id': chat_id,
                'nombre': nombre,
                'profesor_id': profesor_id,
                'fecha_registro': datetime.now().isoformat()
            })

    def obtener_grupos_profesor(self, profesor_id: int) -> List[Tuple[int, str]]:
        if profesor_id is None:
            return []
        query = self.db.collection('grupos').where('profesor_id', '==', profesor_id).stream()
        res = []
        for doc in query:
            d = doc.to_dict()
            res.append((int(d['chat_id']), d['nombre']))
        return res

    def obtener_todos_los_grupos(self) -> List[Tuple[int, str]]:
        docs = self.db.collection('grupos').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            res.append((int(d['chat_id']), d['nombre']))
        return res

    def es_grupo_registrado(self, chat_id: int) -> bool:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        return doc.exists

    def es_grupo_de_profesor(self, chat_id: int, profesor_id: int) -> bool:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            return doc.to_dict().get('profesor_id') == profesor_id
        return False

    def obtener_profesor_de_grupo(self, chat_id: int) -> Optional[int]:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            return doc.to_dict().get('profesor_id')
        return None

    def obtener_grupo(self, chat_id: int) -> Optional[Tuple[int, str]]:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            d = doc.to_dict()
            return (int(d['chat_id']), d['nombre'])
        return None

    def eliminar_grupo(self, chat_id: int):
        self.db.collection('grupos').document(str(chat_id)).delete()

    # --- RECAUDACIONES ---
    def crear_recaudacion(self, profesor_id: int, grupo_id: int, concepto: str, monto: float,
                          banco: str, cedula: str, telefono: str, fecha_limite: str) -> int:
        self.limpiar_recaudacion_anterior(grupo_id)
        
        # Generar un ID numérico único basado en timestamp
        rec_id = int(time.time() * 1000)
        doc_ref = self.db.collection('recaudaciones').document(str(rec_id))
        doc_ref.set({
            'id': rec_id,
            'profesor_id': profesor_id,
            'grupo_id': grupo_id,
            'concepto': concepto,
            'monto': float(monto),
            'banco': banco,
            'cedula': cedula,
            'telefono': telefono,
            'fecha_limite': fecha_limite,
            'activa': 1,
            'mensaje_lista_id': None
        })
        return rec_id

    def limpiar_recaudacion_anterior(self, grupo_id: int):
        recs = self.db.collection('recaudaciones').where('grupo_id', '==', grupo_id).stream()
        for r_doc in recs:
            r_data = r_doc.to_dict()
            r_id = r_data.get('id') or r_doc.id
            
            # Borrar pagos de la recaudación anterior
            pagos = self.db.collection('pagos').where('recaudacion_id', '==', int(r_id)).stream()
            for p in pagos:
                p.reference.delete()
            
            # Desactivar la recaudación
            r_doc.reference.update({'activa': 0})

    def actualizar_mensaje_lista(self, recaudacion_id: int, mensaje_lista_id: int):
        self.db.collection('recaudaciones').document(str(recaudacion_id)).update({
            'mensaje_lista_id': mensaje_lista_id
        })

    def _rec_doc_to_tuple(self, d: dict) -> Tuple:
        return (
            int(d.get('id', 0)),
            int(d.get('profesor_id', 0)),
            int(d.get('grupo_id', 0)),
            d.get('concepto', ''),
            float(d.get('monto', 0.0)),
            d.get('banco', ''),
            d.get('cedula', ''),
            d.get('telefono', ''),
            d.get('fecha_limite', ''),
            int(d.get('activa', 0)),
            d.get('mensaje_lista_id')
        )

    def obtener_recaudacion_activa(self, grupo_id: int) -> Optional[Tuple]:
        recs = self.db.collection('recaudaciones') \
            .where('grupo_id', '==', grupo_id) \
            .where('activa', '==', 1).limit(1).stream()
        for doc in recs:
            return self._rec_doc_to_tuple(doc.to_dict())
        return None

    def obtener_todas_recaudaciones_activas(self) -> List[Tuple]:
        recs = self.db.collection('recaudaciones').where('activa', '==', 1).stream()
        return [self._rec_doc_to_tuple(doc.to_dict()) for doc in recs]

    def finalizar_recaudacion(self, recaudacion_id: int):
        self.db.collection('recaudaciones').document(str(recaudacion_id)).update({'activa': 0})

    # --- PAGOS ---
    def registrar_pago(self, recaudacion_id: int, estudiante_nombre: str, fecha_pago: str,
                       estudiante_id: Optional[int] = None, numero_verificacion: Optional[str] = None):
        pago_id = int(time.time() * 1000)
        self.db.collection('pagos').document(str(pago_id)).set({
            'id': pago_id,
            'recaudacion_id': int(recaudacion_id),
            'estudiante_id': estudiante_id,
            'estudiante_nombre': estudiante_nombre,
            'numero_verificacion': numero_verificacion,
            'fecha_pago': fecha_pago,
            'validado': 1
        })

    def estudiante_ya_pago(self, recaudacion_id: int, estudiante_id: Optional[int], estudiante_nombre: str) -> bool:
        if estudiante_id:
            query = self.db.collection('pagos') \
                .where('recaudacion_id', '==', int(recaudacion_id)) \
                .where('estudiante_id', '==', estudiante_id).limit(1).stream()
            if any(query):
                return True
        
        pagos = self.db.collection('pagos').where('recaudacion_id', '==', int(recaudacion_id)).stream()
        for p in pagos:
            d = p.to_dict()
            if d.get('estudiante_nombre', '').lower() == estudiante_nombre.lower():
                return True
        return False

    def contar_pagos(self, recaudacion_id: int) -> int:
        pagos = self.db.collection('pagos').where('recaudacion_id', '==', int(recaudacion_id)).stream()
        return sum(1 for _ in pagos)

    def obtener_pagos_recaudacion(self, recaudacion_id: int) -> List[Tuple]:
        pagos = self.db.collection('pagos').where('recaudacion_id', '==', int(recaudacion_id)).stream()
        res = []
        for doc in pagos:
            d = doc.to_dict()
            res.append((
                d.get('estudiante_nombre', ''),
                d.get('fecha_pago', ''),
                d.get('estudiante_id'),
                d.get('numero_verificacion')
            ))
        return res

    # --- STRIKES ---
    def agregar_strike(self, estudiante_id: int, estudiante_nombre: str, grupo_id: int, motivo: str):
        strike_id = int(time.time() * 1000)
        self.db.collection('strikes').document(str(strike_id)).set({
            'id': strike_id,
            'estudiante_id': estudiante_id,
            'estudiante_nombre': estudiante_nombre,
            'grupo_id': grupo_id,
            'motivo': motivo,
            'fecha': datetime.now().isoformat()
        })

    def obtener_strikes_estudiante(self, estudiante_id: int, grupo_id: int) -> int:
        strikes = self.db.collection('strikes') \
            .where('estudiante_id', '==', estudiante_id) \
            .where('grupo_id', '==', grupo_id).stream()
        return sum(1 for _ in strikes)

    def obtener_strikes_profesor(self, profesor_id: int) -> List[Tuple]:
        grupos_profesor = self.obtener_grupos_profesor(profesor_id)
        if not grupos_profesor:
            return []
        
        dict_grupos = {g[0]: g[1] for g in grupos_profesor}
        conteo = {} # (estudiante_nombre, grupo_id): count
        
        for g_id in dict_grupos.keys():
            strikes = self.db.collection('strikes').where('grupo_id', '==', g_id).stream()
            for s_doc in strikes:
                d = s_doc.to_dict()
                key = (d.get('estudiante_nombre', ''), g_id)
                conteo[key] = conteo.get(key, 0) + 1
        
        res = []
        for (est_nombre, g_id), total in conteo.items():
            if total > 0:
                res.append((est_nombre, g_id, dict_grupos[g_id], total))
        return res

    def obtener_historial_strikes(self, estudiante_id: int, grupo_id: int) -> List[Tuple]:
        strikes = self.db.collection('strikes') \
            .where('estudiante_id', '==', estudiante_id) \
            .where('grupo_id', '==', grupo_id).stream()
        items = []
        for s in strikes:
            d = s.to_dict()
            items.append((d.get('motivo', ''), d.get('fecha', '')))
        items.sort(key=lambda x: x[1])
        return items

    def obtener_historial_strikes_por_nombre(self, estudiante_nombre: str, grupo_id: int) -> List[Tuple]:
        strikes = self.db.collection('strikes') \
            .where('estudiante_nombre', '==', estudiante_nombre) \
            .where('grupo_id', '==', grupo_id).stream()
        items = []
        for s in strikes:
            d = s.to_dict()
            items.append((d.get('motivo', ''), d.get('fecha', '')))
        items.sort(key=lambda x: x[1])
        return items

    # --- ASESORÍAS ---
    def agregar_asesoria(self, grupo_id: int, grupo_nombre: str, estudiante_nombre: str, pregunta: str) -> int:
        asesoria_id = int(time.time() * 1000)
        self.db.collection('asesorias').document(str(asesoria_id)).set({
            'id': asesoria_id,
            'grupo_id': grupo_id,
            'grupo_nombre': grupo_nombre,
            'estudiante_nombre': estudiante_nombre,
            'pregunta': pregunta,
            'fecha': datetime.now().isoformat(),
            'respondida': 0
        })
        return asesoria_id

    def obtener_asesorias_pendientes(self, profesor_id: int) -> List[Tuple]:
        grupos_profesor = self.obtener_grupos_profesor(profesor_id)
        if not grupos_profesor:
            return []
        
        g_ids = [g[0] for g in grupos_profesor]
        items = []
        
        for g_id in g_ids:
            asesorias = self.db.collection('asesorias') \
                .where('grupo_id', '==', g_id) \
                .where('respondida', '==', 0).stream()
            for a in asesorias:
                d = a.to_dict()
                items.append((
                    int(d.get('id', 0)),
                    d.get('grupo_nombre', ''),
                    d.get('estudiante_nombre', ''),
                    d.get('pregunta', ''),
                    int(d.get('grupo_id', 0)),
                    d.get('fecha', '')
                ))
        items.sort(key=lambda x: x[5])
        return [(i[0], i[1], i[2], i[3], i[4]) for i in items]

    def marcar_asesoria_respondida(self, asesoria_id: int):
        self.db.collection('asesorias').document(str(asesoria_id)).update({'respondida': 1})

    # --- LÍMITE DE ASESORÍAS ---
    def incrementar_contador_asesorias(self, grupo_id: int):
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        doc_id = f"{grupo_id}_{fecha_hoy}"
        doc_ref = self.db.collection('asesorias_limite').document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({'contador': firestore.Increment(1)})
        else:
            doc_ref.set({
                'grupo_id': grupo_id,
                'fecha': fecha_hoy,
                'contador': 1
            })

    def obtener_contador_asesorias(self, grupo_id: int) -> int:
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        doc_id = f"{grupo_id}_{fecha_hoy}"
        doc = self.db.collection('asesorias_limite').document(doc_id).get()
        if doc.exists:
            return int(doc.to_dict().get('contador', 0))
        return 0

    # --- CONFIGURACIÓN ---
    def guardar_config(self, clave: str, valor: str):
        self.db.collection('configuracion').document(clave).set({
            'clave': clave,
            'valor': valor
        })

    def obtener_config(self, clave: str) -> Optional[str]:
        doc = self.db.collection('configuracion').document(clave).get()
        if doc.exists:
            return doc.to_dict().get('valor')
        return None

    def close(self):
        pass
