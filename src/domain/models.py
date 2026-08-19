from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class EstudianteGrupo:
    """Estudiante cargado desde el Excel del profesor, asociado a un grupo"""
    chat_id: int
    cedula: str
    apellidos: str
    nombres: str
    correo: str

@dataclass
class MiembroTelegram:
    """Miembro detectado en un grupo de Telegram (registro pasivo)"""
    user_id: int
    chat_id: int
    first_name: str
    last_name: str
    username: Optional[str] = None
    fecha_visto: Optional[str] = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class PendienteVerificacion:
    """Miembro que no pasó la verificación y tiene plazo para cambiar su nombre"""
    user_id: int
    chat_id: int
    nombre_telegram: str
    fecha_limite: str
    notificado: bool = True
    resuelto: int = 0  # 0=pendiente, 1=verificado, 2=expulsado

@dataclass
class Profesor:
    user_id: int
    username: str
    verificado: bool = False
    fecha_registro: Optional[str] = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Grupo:
    chat_id: int
    nombre: str
    profesor_id: int
    fecha_registro: Optional[str] = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Recaudacion:
    id: Optional[int]
    profesor_id: int
    grupo_id: int
    concepto: str
    monto: float
    banco: str
    cedula: str
    telefono: str
    fecha_limite: str
    activa: bool = True
    mensaje_lista_id: Optional[int] = None

@dataclass
class Pago:
    id: Optional[int]
    recaudacion_id: int
    estudiante_nombre: str
    fecha_pago: str
    validado: bool = True
    estudiante_id: Optional[int] = None
    numero_verificacion: Optional[str] = None

@dataclass
class Strike:
    id: Optional[int]
    estudiante_id: int
    estudiante_nombre: str
    grupo_id: int
    motivo: str
    fecha: str

@dataclass
class Asesoria:
    id: Optional[int]
    grupo_id: int
    grupo_nombre: str
    estudiante_nombre: str
    pregunta: str
    fecha: str
    respondida: bool = False
