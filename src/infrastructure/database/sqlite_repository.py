import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

class SQLiteRepository:
    def __init__(self, db_path: str = 'delegado_virtual.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.crear_tablas()
    
    def crear_tablas(self):
        # Tabla de profesores
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profesores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                verificado INTEGER DEFAULT 0,
                fecha_registro TEXT
            )
        ''')
        
        # Tabla de grupos registrados
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grupos (
                chat_id INTEGER PRIMARY KEY,
                nombre TEXT,
                profesor_id INTEGER,
                fecha_registro TEXT,
                FOREIGN KEY (profesor_id) REFERENCES profesores(user_id)
            )
        ''')
        
        # Tabla de recaudaciones
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS recaudaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profesor_id INTEGER,
                grupo_id INTEGER,
                concepto TEXT,
                monto REAL,
                banco TEXT,
                cedula TEXT,
                telefono TEXT,
                fecha_limite TEXT,
                activa INTEGER DEFAULT 1,
                mensaje_lista_id INTEGER,
                FOREIGN KEY (profesor_id) REFERENCES profesores(user_id),
                FOREIGN KEY (grupo_id) REFERENCES grupos(chat_id)
            )
        ''')
        
        # Tabla de pagos validados
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recaudacion_id INTEGER,
                estudiante_id INTEGER,
                estudiante_nombre TEXT,
                numero_verificacion TEXT,
                fecha_pago TEXT,
                validado INTEGER DEFAULT 1,
                FOREIGN KEY (recaudacion_id) REFERENCES recaudaciones(id)
            )
        ''')
        
        # Tabla de strikes
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS strikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER,
                estudiante_nombre TEXT,
                grupo_id INTEGER,
                motivo TEXT,
                fecha TEXT,
                FOREIGN KEY (grupo_id) REFERENCES grupos(chat_id)
            )
        ''')
        
        # Tabla de solicitudes de asesoría
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS asesorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER,
                grupo_nombre TEXT,
                estudiante_nombre TEXT,
                pregunta TEXT,
                fecha TEXT,
                respondida INTEGER DEFAULT 0,
                FOREIGN KEY (grupo_id) REFERENCES grupos(chat_id)
            )
        ''')
        
        # Tabla de límite diario de asesorías
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS asesorias_limite (
                grupo_id INTEGER,
                fecha TEXT,
                contador INTEGER DEFAULT 0,
                PRIMARY KEY (grupo_id, fecha)
            )
        ''')

        # Tabla de configuración del sistema (ej. API Keys)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')

        # Tabla de estudiantes cargados desde Excel (por grupo)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS estudiantes_grupo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                cedula TEXT,
                apellidos TEXT,
                nombres TEXT,
                correo TEXT,
                FOREIGN KEY (chat_id) REFERENCES grupos(chat_id)
            )
        ''')

        # Tabla de miembros de Telegram detectados (registro pasivo)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS miembros_telegram (
                user_id INTEGER,
                chat_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                fecha_visto TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')

        # Tabla de anuncios oficiales del profesor
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS anuncios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                texto TEXT,
                tipo_media TEXT,
                media_id TEXT,
                fecha_hora TEXT,
                FOREIGN KEY (chat_id) REFERENCES grupos(chat_id)
            )
        ''')

        # Tabla de pendientes de verificación (ultimátum 12h)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pendientes_verificacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                nombre_telegram TEXT,
                fecha_limite TEXT,
                notificado INTEGER DEFAULT 1,
                resuelto INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
        self._migrar_esquema()


    def _migrar_esquema(self):
        """Asegura que columnas agregadas existan en bases de datos anteriores"""
        try:
            cols_rec = [c[1] for c in self.cursor.execute("PRAGMA table_info(recaudaciones)").fetchall()]
            if 'mensaje_lista_id' not in cols_rec:
                self.cursor.execute("ALTER TABLE recaudaciones ADD COLUMN mensaje_lista_id INTEGER")

            cols_pagos = [c[1] for c in self.cursor.execute("PRAGMA table_info(pagos)").fetchall()]
            if 'estudiante_id' not in cols_pagos:
                self.cursor.execute("ALTER TABLE pagos ADD COLUMN estudiante_id INTEGER")
            if 'numero_verificacion' not in cols_pagos:
                self.cursor.execute("ALTER TABLE pagos ADD COLUMN numero_verificacion TEXT")

            cols_pend = [c[1] for c in self.cursor.execute("PRAGMA table_info(pendientes_verificacion)").fetchall()]
            if 'nombre_oficial' not in cols_pend:
                self.cursor.execute("ALTER TABLE pendientes_verificacion ADD COLUMN nombre_oficial TEXT")
            
            self.conn.commit()
        except Exception as e:
            print(f"⚠️ Nota de migración de BD: {e}")
    
    # Métodos para profesores
    def registrar_profesor(self, user_id: int, username: str):
        self.cursor.execute(
            'INSERT OR IGNORE INTO profesores (user_id, username, fecha_registro) VALUES (?, ?, ?)',
            (user_id, username, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def verificar_profesor(self, user_id: int):
        self.cursor.execute('UPDATE profesores SET verificado = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def es_profesor_verificado(self, user_id: int) -> bool:
        self.cursor.execute('SELECT verificado FROM profesores WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return bool(result and result[0] == 1)
    
    # Métodos para grupos
    def registrar_grupo(self, chat_id: int, nombre: str, profesor_id: int):
        self.cursor.execute(
            'INSERT OR IGNORE INTO grupos (chat_id, nombre, profesor_id, fecha_registro) VALUES (?, ?, ?, ?)',
            (chat_id, nombre, profesor_id, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def obtener_grupos_profesor(self, profesor_id: int) -> List[Tuple[int, str]]:
        if profesor_id is None:
            return []
        self.cursor.execute('SELECT chat_id, nombre FROM grupos WHERE profesor_id = ?', (profesor_id,))
        return self.cursor.fetchall()

    def obtener_todos_los_grupos(self) -> List[Tuple[int, str]]:
        self.cursor.execute('SELECT chat_id, nombre FROM grupos')
        return self.cursor.fetchall()

    def es_grupo_registrado(self, chat_id: int) -> bool:
        self.cursor.execute('SELECT 1 FROM grupos WHERE chat_id = ?', (chat_id,))
        return self.cursor.fetchone() is not None

    def es_grupo_de_profesor(self, chat_id: int, profesor_id: int) -> bool:
        """Verifica que un grupo pertenezca a un profesor específico."""
        self.cursor.execute(
            'SELECT 1 FROM grupos WHERE chat_id = ? AND profesor_id = ?',
            (chat_id, profesor_id)
        )
        return self.cursor.fetchone() is not None

    def obtener_profesor_de_grupo(self, chat_id: int) -> Optional[int]:
        self.cursor.execute('SELECT profesor_id FROM grupos WHERE chat_id = ?', (chat_id,))
        res = self.cursor.fetchone()
        return res[0] if res else None

    def obtener_grupo(self, chat_id: int) -> Optional[Tuple[int, str]]:
        self.cursor.execute('SELECT chat_id, nombre FROM grupos WHERE chat_id = ?', (chat_id,))
        return self.cursor.fetchone()
    
    def eliminar_grupo(self, chat_id: int):
        self.cursor.execute('DELETE FROM grupos WHERE chat_id = ?', (chat_id,))
        self.conn.commit()
    
    # Métodos para recaudaciones
    def crear_recaudacion(self, profesor_id: int, grupo_id: int, concepto: str, monto: float,
                          banco: str, cedula: str, telefono: str, fecha_limite: str) -> int:
        # Desactivar recaudación previa del grupo y borrar sus pagos (nueva recaudación limpia los datos anteriores)
        self.limpiar_recaudacion_anterior(grupo_id)

        self.cursor.execute('''
            INSERT INTO recaudaciones (profesor_id, grupo_id, concepto, monto, banco, cedula, telefono, fecha_limite, activa)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (profesor_id, grupo_id, concepto, monto, banco, cedula, telefono, fecha_limite))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def limpiar_recaudacion_anterior(self, grupo_id: int):
        """Elimina recaudaciones anteriores activas y sus pagos para el grupo"""
        self.cursor.execute('SELECT id FROM recaudaciones WHERE grupo_id = ?', (grupo_id,))
        rec_ids = [row[0] for row in self.cursor.fetchall()]
        for r_id in rec_ids:
            self.cursor.execute('DELETE FROM pagos WHERE recaudacion_id = ?', (r_id,))
        self.cursor.execute('UPDATE recaudaciones SET activa = 0 WHERE grupo_id = ?', (grupo_id,))
        self.conn.commit()
    
    def actualizar_mensaje_lista(self, recaudacion_id: int, mensaje_lista_id: int):
        self.cursor.execute('UPDATE recaudaciones SET mensaje_lista_id = ? WHERE id = ?', (mensaje_lista_id, recaudacion_id))
        self.conn.commit()
    
    def obtener_recaudacion_activa(self, grupo_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            'SELECT * FROM recaudaciones WHERE grupo_id = ? AND activa = 1',
            (grupo_id,)
        )
        return self.cursor.fetchone()

    def obtener_todas_recaudaciones_activas(self) -> List[Tuple]:
        self.cursor.execute('SELECT * FROM recaudaciones WHERE activa = 1')
        return self.cursor.fetchall()
    
    def finalizar_recaudacion(self, recaudacion_id: int):
        self.cursor.execute('UPDATE recaudaciones SET activa = 0 WHERE id = ?', (recaudacion_id,))
        self.conn.commit()
    
    # Métodos para pagos
    def registrar_pago(self, recaudacion_id: int, estudiante_nombre: str, fecha_pago: str,
                       estudiante_id: Optional[int] = None, numero_verificacion: Optional[str] = None):
        self.cursor.execute(
            '''INSERT INTO pagos (recaudacion_id, estudiante_id, estudiante_nombre, numero_verificacion, fecha_pago, validado)
               VALUES (?, ?, ?, ?, ?, 1)''',
            (recaudacion_id, estudiante_id, estudiante_nombre, numero_verificacion, fecha_pago)
        )
        self.conn.commit()

    def estudiante_ya_pago(self, recaudacion_id: int, estudiante_id: Optional[int], estudiante_nombre: str) -> bool:
        if estudiante_id:
            self.cursor.execute(
                'SELECT 1 FROM pagos WHERE recaudacion_id = ? AND estudiante_id = ?',
                (recaudacion_id, estudiante_id)
            )
            if self.cursor.fetchone():
                return True
        self.cursor.execute(
            'SELECT 1 FROM pagos WHERE recaudacion_id = ? AND LOWER(estudiante_nombre) = LOWER(?)',
            (recaudacion_id, estudiante_nombre)
        )
        return self.cursor.fetchone() is not None

    def contar_pagos(self, recaudacion_id: int) -> int:
        self.cursor.execute('SELECT COUNT(*) FROM pagos WHERE recaudacion_id = ?', (recaudacion_id,))
        res = self.cursor.fetchone()
        return res[0] if res else 0
    
    def obtener_pagos_recaudacion(self, recaudacion_id: int) -> List[Tuple]:
        self.cursor.execute(
            'SELECT estudiante_nombre, fecha_pago, estudiante_id, numero_verificacion FROM pagos WHERE recaudacion_id = ? ORDER BY id',
            (recaudacion_id,)
        )
        return self.cursor.fetchall()
    
    # Métodos para strikes
    def agregar_strike(self, estudiante_id: int, estudiante_nombre: str, grupo_id: int, motivo: str):
        self.cursor.execute(
            'INSERT INTO strikes (estudiante_id, estudiante_nombre, grupo_id, motivo, fecha) VALUES (?, ?, ?, ?, ?)',
            (estudiante_id, estudiante_nombre, grupo_id, motivo, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def obtener_strikes_estudiante(self, estudiante_id: int, grupo_id: int) -> int:
        self.cursor.execute(
            'SELECT COUNT(*) FROM strikes WHERE estudiante_id = ? AND grupo_id = ?',
            (estudiante_id, grupo_id)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def obtener_strikes_profesor(self, profesor_id: int) -> List[Tuple]:
        self.cursor.execute('''
            SELECT s.estudiante_nombre, s.grupo_id, g.nombre, COUNT(*) as total
            FROM strikes s
            JOIN grupos g ON s.grupo_id = g.chat_id
            WHERE g.profesor_id = ?
            GROUP BY s.estudiante_id, s.grupo_id
            HAVING total > 0
        ''', (profesor_id,))
        return self.cursor.fetchall()
    
    def obtener_historial_strikes(self, estudiante_id: int, grupo_id: int) -> List[Tuple]:
        self.cursor.execute(
            'SELECT motivo, fecha FROM strikes WHERE estudiante_id = ? AND grupo_id = ? ORDER BY fecha',
            (estudiante_id, grupo_id)
        )
        return self.cursor.fetchall()
    
    def obtener_historial_strikes_por_nombre(self, estudiante_nombre: str, grupo_id: int) -> List[Tuple]:
        """Obtiene el historial de strikes por nombre de estudiante (CORREGIDO INDENTACIÓN)"""
        self.cursor.execute(
            'SELECT motivo, fecha FROM strikes WHERE estudiante_nombre = ? AND grupo_id = ? ORDER BY fecha',
            (estudiante_nombre, grupo_id)
        )
        return self.cursor.fetchall()
    
    # Métodos para asesorías
    def agregar_asesoria(self, grupo_id: int, grupo_nombre: str, estudiante_nombre: str, pregunta: str) -> int:
        self.cursor.execute(
            'INSERT INTO asesorias (grupo_id, grupo_nombre, estudiante_nombre, pregunta, fecha) VALUES (?, ?, ?, ?, ?)',
            (grupo_id, grupo_nombre, estudiante_nombre, pregunta, datetime.now().isoformat())
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def obtener_asesorias_pendientes(self, profesor_id: int) -> List[Tuple]:
        self.cursor.execute('''
            SELECT a.id, a.grupo_nombre, a.estudiante_nombre, a.pregunta, a.grupo_id
            FROM asesorias a
            JOIN grupos g ON a.grupo_id = g.chat_id
            WHERE g.profesor_id = ? AND a.respondida = 0
            ORDER BY a.fecha
        ''', (profesor_id,))
        return self.cursor.fetchall()
    
    def marcar_asesoria_respondida(self, asesoria_id: int):
        self.cursor.execute('UPDATE asesorias SET respondida = 1 WHERE id = ?', (asesoria_id,))
        self.conn.commit()
    
    # Métodos para límite de asesorías
    def incrementar_contador_asesorias(self, grupo_id: int):
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('''
            INSERT INTO asesorias_limite (grupo_id, fecha, contador)
            VALUES (?, ?, 1)
            ON CONFLICT(grupo_id, fecha) DO UPDATE SET contador = contador + 1
        ''', (grupo_id, fecha_hoy))
        self.conn.commit()
    
    def obtener_contador_asesorias(self, grupo_id: int) -> int:
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute(
            'SELECT contador FROM asesorias_limite WHERE grupo_id = ? AND fecha = ?',
            (grupo_id, fecha_hoy)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0

    # Métodos para configuración clave-valor
    def guardar_config(self, clave: str, valor: str):
        self.cursor.execute('''
            INSERT INTO configuracion (clave, valor)
            VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
        ''', (clave, valor))
        self.conn.commit()

    def obtener_config(self, clave: str) -> Optional[str]:
        self.cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))
        res = self.cursor.fetchone()
        return res[0] if res else None
    
    # --- ESTUDIANTES DE GRUPO (desde Excel) ---
    def guardar_estudiante_grupo(self, chat_id: int, cedula: str, apellidos: str, nombres: str, correo: str):
        self.cursor.execute(
            'INSERT INTO estudiantes_grupo (chat_id, cedula, apellidos, nombres, correo) VALUES (?, ?, ?, ?, ?)',
            (chat_id, cedula, apellidos, nombres, correo)
        )
        self.conn.commit()

    def obtener_estudiantes_grupo(self, chat_id: int) -> List[Tuple]:
        self.cursor.execute(
            'SELECT cedula, apellidos, nombres, correo FROM estudiantes_grupo WHERE chat_id = ?',
            (chat_id,)
        )
        return self.cursor.fetchall()

    def buscar_estudiante_por_cedula(self, chat_id: int, cedula: str) -> Optional[Tuple]:
        import re
        cedula_clean = re.sub(r'\D', '', cedula or '')
        if not cedula_clean:
            return None
        self.cursor.execute(
            'SELECT id, chat_id, cedula, apellidos, nombres, correo FROM estudiantes_grupo WHERE chat_id = ?',
            (chat_id,)
        )
        filas = self.cursor.fetchall()
        for f in filas:
            c_db = re.sub(r'\D', '', str(f[2] or ''))
            if c_db == cedula_clean:
                return f
        return None

    def eliminar_estudiantes_grupo(self, chat_id: int):
        self.cursor.execute('DELETE FROM estudiantes_grupo WHERE chat_id = ?', (chat_id,))
        self.conn.commit()

    # --- MIEMBROS DE TELEGRAM (registro pasivo) ---
    def registrar_miembro_telegram(self, chat_id: int, user_id: int, first_name: str, last_name: str, username: str):
        self.cursor.execute('''
            INSERT INTO miembros_telegram (user_id, chat_id, first_name, last_name, username, fecha_visto)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                fecha_visto = excluded.fecha_visto
        ''', (user_id, chat_id, first_name, last_name, username, datetime.now().isoformat()))
        self.conn.commit()

    def obtener_miembros_telegram(self, chat_id: int) -> List[Tuple]:
        self.cursor.execute(
            'SELECT user_id, first_name, last_name, username FROM miembros_telegram WHERE chat_id = ?',
            (chat_id,)
        )
        return self.cursor.fetchall()

    # --- PENDIENTES DE VERIFICACIÓN ---
    def agregar_pendiente_verificacion(self, user_id: int, chat_id: int, nombre_telegram: str, fecha_limite: str, nombre_oficial: str = ""):
        # Eliminar pendiente anterior si existe para este usuario/grupo
        self.cursor.execute(
            'DELETE FROM pendientes_verificacion WHERE user_id = ? AND chat_id = ?',
            (user_id, chat_id)
        )
        self.cursor.execute(
            'INSERT INTO pendientes_verificacion (user_id, chat_id, nombre_telegram, fecha_limite, notificado, resuelto, nombre_oficial) VALUES (?, ?, ?, ?, 1, 0, ?)',
            (user_id, chat_id, nombre_telegram, fecha_limite, nombre_oficial)
        )
        self.conn.commit()

    def obtener_pendientes_activos(self) -> List[Tuple]:
        self.cursor.execute(
            'SELECT user_id, chat_id, nombre_telegram, fecha_limite, notificado, resuelto, nombre_oficial '
            'FROM pendientes_verificacion WHERE resuelto = 0'
        )
        return self.cursor.fetchall()

    def resolver_pendiente(self, user_id: int, chat_id: int, estado: int):
        self.cursor.execute(
            'UPDATE pendientes_verificacion SET resuelto = ? WHERE user_id = ? AND chat_id = ?',
            (estado, user_id, chat_id)
        )
        self.conn.commit()

    def es_estudiante_verificado(self, user_id: int) -> bool:
        self.cursor.execute(
            'SELECT 1 FROM pendientes_verificacion WHERE user_id = ? AND resuelto = 1',
            (user_id,)
        )
        return self.cursor.fetchone() is not None

    def guardar_anuncio(self, chat_id: int, texto: str, tipo_media: str = None, media_id: str = None):
        from datetime import datetime
        fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        self.cursor.execute(
            'INSERT INTO anuncios (chat_id, texto, tipo_media, media_id, fecha_hora) VALUES (?, ?, ?, ?, ?)',
            (chat_id, texto, tipo_media, media_id, fecha_str)
        )
        self.conn.commit()

    def obtener_ultimo_anuncio(self, chat_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            'SELECT texto, tipo_media, media_id, fecha_hora FROM anuncios WHERE chat_id = ? ORDER BY id DESC LIMIT 1',
            (chat_id,)
        )
        return self.cursor.fetchone()

    def eliminar_anuncios_grupo(self, chat_id: int):
        self.cursor.execute('DELETE FROM anuncios WHERE chat_id = ?', (chat_id,))
        self.conn.commit()

    def guardar_material(self, chat_id: int, tipo: str, contenido: str, descripcion: str = None):
        from datetime import datetime
        fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        self.cursor.execute(
            'INSERT INTO materiales (chat_id, tipo, contenido, descripcion, fecha_hora) VALUES (?, ?, ?, ?, ?)',
            (chat_id, tipo, str(contenido), descripcion, fecha_str)
        )
        self.conn.commit()

    def eliminar_materiales_grupo(self, chat_id: int):
        self.cursor.execute('DELETE FROM materiales WHERE chat_id = ?', (chat_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

