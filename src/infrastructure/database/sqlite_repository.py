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
                FOREIGN KEY (profesor_id) REFERENCES profesores(user_id),
                FOREIGN KEY (grupo_id) REFERENCES grupos(chat_id)
            )
        ''')
        
        # Tabla de pagos validados
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recaudacion_id INTEGER,
                estudiante_nombre TEXT,
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
        
        self.conn.commit()
    
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
            return self.obtener_todos_los_grupos()
        self.cursor.execute('SELECT chat_id, nombre FROM grupos WHERE profesor_id = ?', (profesor_id,))
        return self.cursor.fetchall()

    def obtener_todos_los_grupos(self) -> List[Tuple[int, str]]:
        self.cursor.execute('SELECT chat_id, nombre FROM grupos')
        return self.cursor.fetchall()

    def es_grupo_registrado(self, chat_id: int) -> bool:
        self.cursor.execute('SELECT 1 FROM grupos WHERE chat_id = ?', (chat_id,))
        return self.cursor.fetchone() is not None

    def obtener_profesor_de_grupo(self, chat_id: int) -> Optional[int]:
        self.cursor.execute('SELECT profesor_id FROM grupos WHERE chat_id = ?', (chat_id,))
        res = self.cursor.fetchone()
        return res[0] if res else None
    
    def eliminar_grupo(self, chat_id: int):
        self.cursor.execute('DELETE FROM grupos WHERE chat_id = ?', (chat_id,))
        self.conn.commit()
    
    # Métodos para recaudaciones
    def crear_recaudacion(self, profesor_id: int, grupo_id: int, concepto: str, monto: float,
                          banco: str, cedula: str, telefono: str, fecha_limite: str) -> int:
        self.cursor.execute('''
            INSERT INTO recaudaciones (profesor_id, grupo_id, concepto, monto, banco, cedula, telefono, fecha_limite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (profesor_id, grupo_id, concepto, monto, banco, cedula, telefono, fecha_limite))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def obtener_recaudacion_activa(self, grupo_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            'SELECT * FROM recaudaciones WHERE grupo_id = ? AND activa = 1',
            (grupo_id,)
        )
        return self.cursor.fetchone()
    
    def finalizar_recaudacion(self, recaudacion_id: int):
        self.cursor.execute('UPDATE recaudaciones SET activa = 0 WHERE id = ?', (recaudacion_id,))
        self.conn.commit()
    
    # Métodos para pagos
    def registrar_pago(self, recaudacion_id: int, estudiante_nombre: str, fecha_pago: str):
        self.cursor.execute(
            'INSERT INTO pagos (recaudacion_id, estudiante_nombre, fecha_pago) VALUES (?, ?, ?)',
            (recaudacion_id, estudiante_nombre, fecha_pago)
        )
        self.conn.commit()
    
    def obtener_pagos_recaudacion(self, recaudacion_id: int) -> List[Tuple]:
        self.cursor.execute(
            'SELECT estudiante_nombre, fecha_pago FROM pagos WHERE recaudacion_id = ? ORDER BY id',
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
    def agregar_asesoria(self, grupo_id: int, grupo_nombre: str, estudiante_nombre: str, pregunta: str):
        self.cursor.execute(
            'INSERT INTO asesorias (grupo_id, grupo_nombre, estudiante_nombre, pregunta, fecha) VALUES (?, ?, ?, ?, ?)',
            (grupo_id, grupo_nombre, estudiante_nombre, pregunta, datetime.now().isoformat())
        )
        self.conn.commit()
    
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
    
    def close(self):
        self.conn.close()
