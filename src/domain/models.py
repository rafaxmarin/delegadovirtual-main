from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

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

@dataclass
class Pago:
    id: Optional[int]
    recaudacion_id: int
    estudiante_nombre: str
    fecha_pago: str
    validado: bool = True

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
