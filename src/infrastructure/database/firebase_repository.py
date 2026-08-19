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

    def _to_int(self, val, default=0) -> int:
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    # --- PROFESORES ---
    def registrar_profesor(self, user_id: int, username: str):
        doc_ref = self.db.collection('profesores').document(str(user_id))
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set({
                'user_id': self._to_int(user_id),
                'username': username or '',
                'verificado': 0,
                'fecha_registro': datetime.now().isoformat()
            })

    def verificar_profesor(self, user_id: int):
        doc_ref = self.db.collection('profesores').document(str(user_id))
        doc_ref.set({'verificado': 1}, merge=True)

    def es_profesor_verificado(self, user_id: int) -> bool:
        doc = self.db.collection('profesores').document(str(user_id)).get()
        if doc.exists:
            data = doc.to_dict()
            return data.get('verificado') in (1, True)
        return False

    # --- GRUPOS ---
    def registrar_grupo(self, chat_id: int, nombre: str, profesor_id: int):
        doc_ref = self.db.collection('grupos').document(str(chat_id))
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set({
                'chat_id': self._to_int(chat_id),
                'nombre': nombre or '',
                'profesor_id': self._to_int(profesor_id),
                'fecha_registro': datetime.now().isoformat()
            })

    def obtener_grupos_profesor(self, profesor_id: int) -> List[Tuple[int, str]]:
        if profesor_id is None:
            return []
        target_pid = self._to_int(profesor_id)
        docs = self.db.collection('grupos').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            if self._to_int(d.get('profesor_id')) == target_pid:
                res.append((self._to_int(d.get('chat_id')), d.get('nombre', '')))
        return res

    def obtener_todos_los_grupos(self) -> List[Tuple[int, str]]:
        docs = self.db.collection('grupos').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            res.append((self._to_int(d.get('chat_id')), d.get('nombre', '')))
        return res

    def es_grupo_registrado(self, chat_id: int) -> bool:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        return doc.exists

    def es_grupo_de_profesor(self, chat_id: int, profesor_id: int) -> bool:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            return self._to_int(doc.to_dict().get('profesor_id')) == self._to_int(profesor_id)
        return False

    def obtener_profesor_de_grupo(self, chat_id: int) -> Optional[int]:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            return self._to_int(doc.to_dict().get('profesor_id'))
        return None

    def obtener_grupo(self, chat_id: int) -> Optional[Tuple[int, str]]:
        doc = self.db.collection('grupos').document(str(chat_id)).get()
        if doc.exists:
            d = doc.to_dict()
            return (self._to_int(d.get('chat_id')), d.get('nombre', ''))
        return None

    def eliminar_grupo(self, chat_id: int):
        self.db.collection('grupos').document(str(chat_id)).delete()

    # --- RECAUDACIONES ---
    def crear_recaudacion(self, profesor_id: int, grupo_id: int, concepto: str, monto: float,
                          banco: str, cedula: str, telefono: str, fecha_limite: str) -> int:
        self.limpiar_recaudacion_anterior(grupo_id)
        
        rec_id = int(time.time_ns() // 1000)
        doc_ref = self.db.collection('recaudaciones').document(str(rec_id))
        doc_ref.set({
            'id': rec_id,
            'profesor_id': self._to_int(profesor_id),
            'grupo_id': self._to_int(grupo_id),
            'concepto': concepto or '',
            'monto': float(monto or 0.0),
            'banco': banco or '',
            'cedula': cedula or '',
            'telefono': telefono or '',
            'fecha_limite': fecha_limite or '',
            'activa': 1,
            'mensaje_lista_id': None
        })
        return rec_id

    def limpiar_recaudacion_anterior(self, grupo_id: int):
        target_gid = self._to_int(grupo_id)
        recs = self.db.collection('recaudaciones').stream()
        for r_doc in recs:
            r_data = r_doc.to_dict()
            if self._to_int(r_data.get('grupo_id')) == target_gid:
                r_id = self._to_int(r_data.get('id')) or r_doc.id
                
                # Borrar pagos asociados
                pagos = self.db.collection('pagos').stream()
                for p in pagos:
                    p_data = p.to_dict()
                    if self._to_int(p_data.get('recaudacion_id')) == self._to_int(r_id):
                        p.reference.delete()
                
                # Desactivar recaudación
                r_doc.reference.set({'activa': 0}, merge=True)

    def actualizar_mensaje_lista(self, recaudacion_id: int, mensaje_lista_id: int):
        self.db.collection('recaudaciones').document(str(recaudacion_id)).set({
            'mensaje_lista_id': self._to_int(mensaje_lista_id)
        }, merge=True)

    def _rec_doc_to_tuple(self, d: dict) -> Tuple:
        return (
            self._to_int(d.get('id')),
            self._to_int(d.get('profesor_id')),
            self._to_int(d.get('grupo_id')),
            d.get('concepto', ''),
            float(d.get('monto', 0.0)),
            d.get('banco', ''),
            d.get('cedula', ''),
            d.get('telefono', ''),
            d.get('fecha_limite', ''),
            1 if d.get('activa') in (1, True) else 0,
            d.get('mensaje_lista_id')
        )

    def obtener_recaudacion_activa(self, grupo_id: int) -> Optional[Tuple]:
        target_gid = self._to_int(grupo_id)
        recs = self.db.collection('recaudaciones').stream()
        for doc in recs:
            d = doc.to_dict()
            if self._to_int(d.get('grupo_id')) == target_gid and d.get('activa') in (1, True):
                return self._rec_doc_to_tuple(d)
        return None

    def obtener_todas_recaudaciones_activas(self) -> List[Tuple]:
        recs = self.db.collection('recaudaciones').stream()
        res = []
        for doc in recs:
            d = doc.to_dict()
            if d.get('activa') in (1, True):
                res.append(self._rec_doc_to_tuple(d))
        return res

    def finalizar_recaudacion(self, recaudacion_id: int):
        self.db.collection('recaudaciones').document(str(recaudacion_id)).set({'activa': 0}, merge=True)

    # --- PAGOS ---
    def registrar_pago(self, recaudacion_id: int, estudiante_nombre: str, fecha_pago: str,
                       estudiante_id: Optional[int] = None, numero_verificacion: Optional[str] = None):
        pago_id = int(time.time_ns() // 1000)
        self.db.collection('pagos').document(str(pago_id)).set({
            'id': pago_id,
            'recaudacion_id': self._to_int(recaudacion_id),
            'estudiante_id': self._to_int(estudiante_id) if estudiante_id is not None else None,
            'estudiante_nombre': estudiante_nombre or '',
            'numero_verificacion': numero_verificacion or '',
            'fecha_pago': fecha_pago or '',
            'validado': 1
        })

    def estudiante_ya_pago(self, recaudacion_id: int, estudiante_id: Optional[int], estudiante_nombre: str) -> bool:
        target_rec_id = self._to_int(recaudacion_id)
        target_est_id = self._to_int(estudiante_id) if estudiante_id else None
        target_name = (estudiante_nombre or '').lower().strip()

        pagos = self.db.collection('pagos').stream()
        for p in pagos:
            d = p.to_dict()
            if self._to_int(d.get('recaudacion_id')) == target_rec_id:
                if target_est_id and self._to_int(d.get('estudiante_id')) == target_est_id:
                    return True
                if target_name and d.get('estudiante_nombre', '').lower().strip() == target_name:
                    return True
        return False

    def contar_pagos(self, recaudacion_id: int) -> int:
        target_rec_id = self._to_int(recaudacion_id)
        pagos = self.db.collection('pagos').stream()
        count = 0
        for p in pagos:
            d = p.to_dict()
            if self._to_int(d.get('recaudacion_id')) == target_rec_id:
                count += 1
        return count

    def obtener_pagos_recaudacion(self, recaudacion_id: int) -> List[Tuple]:
        target_rec_id = self._to_int(recaudacion_id)
        pagos = self.db.collection('pagos').stream()
        res = []
        for doc in pagos:
            d = doc.to_dict()
            if self._to_int(d.get('recaudacion_id')) == target_rec_id:
                res.append((
                    d.get('estudiante_nombre', ''),
                    d.get('fecha_pago', ''),
                    self._to_int(d.get('estudiante_id')) if d.get('estudiante_id') is not None else None,
                    d.get('numero_verificacion')
                ))
        return res

    # --- STRIKES ---
    def agregar_strike(self, estudiante_id: int, estudiante_nombre: str, grupo_id: int, motivo: str):
        strike_id = int(time.time_ns() // 1000)
        self.db.collection('strikes').document(str(strike_id)).set({
            'id': strike_id,
            'estudiante_id': self._to_int(estudiante_id),
            'estudiante_nombre': estudiante_nombre or '',
            'grupo_id': self._to_int(grupo_id),
            'motivo': motivo or '',
            'fecha': datetime.now().isoformat()
        })

    def obtener_strikes_estudiante(self, estudiante_id: int, grupo_id: int) -> int:
        target_est_id = self._to_int(estudiante_id)
        target_gid = self._to_int(grupo_id)
        strikes = self.db.collection('strikes').stream()
        count = 0
        for s in strikes:
            d = s.to_dict()
            if self._to_int(d.get('estudiante_id')) == target_est_id and self._to_int(d.get('grupo_id')) == target_gid:
                count += 1
        return count

    def obtener_strikes_profesor(self, profesor_id: int) -> List[Tuple]:
        grupos_profesor = self.obtener_grupos_profesor(profesor_id)
        if not grupos_profesor:
            return []
        
        dict_grupos = {g[0]: g[1] for g in grupos_profesor}
        conteo = {}
        
        strikes = self.db.collection('strikes').stream()
        for s_doc in strikes:
            d = s_doc.to_dict()
            g_id = self._to_int(d.get('grupo_id'))
            if g_id in dict_grupos:
                key = (d.get('estudiante_nombre', ''), g_id)
                conteo[key] = conteo.get(key, 0) + 1
        
        res = []
        for (est_nombre, g_id), total in conteo.items():
            if total > 0:
                res.append((est_nombre, g_id, dict_grupos[g_id], total))
        return res

    def obtener_historial_strikes(self, estudiante_id: int, grupo_id: int) -> List[Tuple]:
        target_est_id = self._to_int(estudiante_id)
        target_gid = self._to_int(grupo_id)
        strikes = self.db.collection('strikes').stream()
        items = []
        for s in strikes:
            d = s.to_dict()
            if self._to_int(d.get('estudiante_id')) == target_est_id and self._to_int(d.get('grupo_id')) == target_gid:
                items.append((d.get('motivo', ''), d.get('fecha', '')))
        items.sort(key=lambda x: x[1])
        return items

    def obtener_historial_strikes_por_nombre(self, estudiante_nombre: str, grupo_id: int) -> List[Tuple]:
        target_name = (estudiante_nombre or '').lower().strip()
        target_gid = self._to_int(grupo_id)
        strikes = self.db.collection('strikes').stream()
        items = []
        for s in strikes:
            d = s.to_dict()
            if d.get('estudiante_nombre', '').lower().strip() == target_name and self._to_int(d.get('grupo_id')) == target_gid:
                items.append((d.get('motivo', ''), d.get('fecha', '')))
        items.sort(key=lambda x: x[1])
        return items

    # --- ASESORÍAS ---
    def agregar_asesoria(self, grupo_id: int, grupo_nombre: str, estudiante_nombre: str, pregunta: str) -> int:
        asesoria_id = int(time.time_ns() // 1000)
        self.db.collection('asesorias').document(str(asesoria_id)).set({
            'id': asesoria_id,
            'grupo_id': self._to_int(grupo_id),
            'grupo_nombre': grupo_nombre or '',
            'estudiante_nombre': estudiante_nombre or '',
            'pregunta': pregunta or '',
            'fecha': datetime.now().isoformat(),
            'respondida': 0
        })
        return asesoria_id

    def obtener_asesorias_pendientes(self, profesor_id: int) -> List[Tuple]:
        grupos_profesor = self.obtener_grupos_profesor(profesor_id)
        if not grupos_profesor:
            return []
        
        g_ids = {g[0] for g in grupos_profesor}
        items = []
        
        asesorias = self.db.collection('asesorias').stream()
        for a in asesorias:
            d = a.to_dict()
            g_id = self._to_int(d.get('grupo_id'))
            if g_id in g_ids and d.get('respondida') in (0, False):
                items.append((
                    self._to_int(d.get('id')),
                    d.get('grupo_nombre', ''),
                    d.get('estudiante_nombre', ''),
                    d.get('pregunta', ''),
                    g_id,
                    d.get('fecha', '')
                ))
        items.sort(key=lambda x: x[5])
        return [(i[0], i[1], i[2], i[3], i[4]) for i in items]

    def marcar_asesoria_respondida(self, asesoria_id: int):
        self.db.collection('asesorias').document(str(asesoria_id)).set({'respondida': 1}, merge=True)

    # --- LÍMITE DE ASESORÍAS ---
    def incrementar_contador_asesorias(self, grupo_id: int):
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        doc_id = f"{self._to_int(grupo_id)}_{fecha_hoy}"
        doc_ref = self.db.collection('asesorias_limite').document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.set({'contador': firestore.Increment(1)}, merge=True)
        else:
            doc_ref.set({
                'grupo_id': self._to_int(grupo_id),
                'fecha': fecha_hoy,
                'contador': 1
            })

    def obtener_contador_asesorias(self, grupo_id: int) -> int:
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        doc_id = f"{self._to_int(grupo_id)}_{fecha_hoy}"
        doc = self.db.collection('asesorias_limite').document(doc_id).get()
        if doc.exists:
            return self._to_int(doc.to_dict().get('contador'))
        return 0

    # --- CONFIGURACIÓN ---
    def guardar_config(self, clave: str, valor: str):
        self.db.collection('configuracion').document(clave).set({
            'clave': clave,
            'valor': valor or ''
        })

    def obtener_config(self, clave: str) -> Optional[str]:
        doc = self.db.collection('configuracion').document(clave).get()
        if doc.exists:
            return doc.to_dict().get('valor')
        return None

    # --- ESTUDIANTES DE GRUPO (desde Excel) ---
    def guardar_estudiante_grupo(self, chat_id: int, cedula: str, apellidos: str, nombres: str, correo: str):
        doc_id = f"{self._to_int(chat_id)}_{cedula}"
        self.db.collection('estudiantes_grupo').document(doc_id).set({
            'chat_id': self._to_int(chat_id),
            'cedula': cedula or '',
            'apellidos': apellidos or '',
            'nombres': nombres or '',
            'correo': correo or ''
        })

    def obtener_estudiantes_grupo(self, chat_id: int) -> List[Tuple]:
        target_cid = self._to_int(chat_id)
        docs = self.db.collection('estudiantes_grupo').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            if self._to_int(d.get('chat_id')) == target_cid:
                res.append((
                    d.get('cedula', ''),
                    d.get('apellidos', ''),
                    d.get('nombres', ''),
                    d.get('correo', '')
                ))
        return res

    def eliminar_estudiantes_grupo(self, chat_id: int):
        target_cid = self._to_int(chat_id)
        docs = self.db.collection('estudiantes_grupo').stream()
        for doc in docs:
            d = doc.to_dict()
            if self._to_int(d.get('chat_id')) == target_cid:
                doc.reference.delete()

    # --- MIEMBROS DE TELEGRAM (registro pasivo) ---
    def registrar_miembro_telegram(self, chat_id: int, user_id: int, first_name: str, last_name: str, username: str):
        doc_id = f"{self._to_int(chat_id)}_{self._to_int(user_id)}"
        self.db.collection('miembros_telegram').document(doc_id).set({
            'user_id': self._to_int(user_id),
            'chat_id': self._to_int(chat_id),
            'first_name': first_name or '',
            'last_name': last_name or '',
            'username': username or '',
            'fecha_visto': datetime.now().isoformat()
        })

    def obtener_miembros_telegram(self, chat_id: int) -> List[Tuple]:
        target_cid = self._to_int(chat_id)
        docs = self.db.collection('miembros_telegram').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            if self._to_int(d.get('chat_id')) == target_cid:
                res.append((
                    self._to_int(d.get('user_id')),
                    d.get('first_name', ''),
                    d.get('last_name', ''),
                    d.get('username', '')
                ))
        return res

    # --- PENDIENTES DE VERIFICACIÓN ---
    def agregar_pendiente_verificacion(self, user_id: int, chat_id: int, nombre_telegram: str, fecha_limite: str):
        doc_id = f"{self._to_int(chat_id)}_{self._to_int(user_id)}"
        self.db.collection('pendientes_verificacion').document(doc_id).set({
            'user_id': self._to_int(user_id),
            'chat_id': self._to_int(chat_id),
            'nombre_telegram': nombre_telegram or '',
            'fecha_limite': fecha_limite or '',
            'notificado': 1,
            'resuelto': 0
        })

    def obtener_pendientes_activos(self) -> List[Tuple]:
        docs = self.db.collection('pendientes_verificacion').stream()
        res = []
        for doc in docs:
            d = doc.to_dict()
            if d.get('resuelto') in (0, False):
                res.append((
                    self._to_int(d.get('user_id')),
                    self._to_int(d.get('chat_id')),
                    d.get('nombre_telegram', ''),
                    d.get('fecha_limite', ''),
                    self._to_int(d.get('notificado')),
                    self._to_int(d.get('resuelto'))
                ))
        return res

    def resolver_pendiente(self, user_id: int, chat_id: int, estado: int):
        doc_id = f"{self._to_int(chat_id)}_{self._to_int(user_id)}"
        self.db.collection('pendientes_verificacion').document(doc_id).set(
            {'resuelto': estado}, merge=True
        )

    def close(self):
        pass
