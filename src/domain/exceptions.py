class DomainException(Exception):
    """Excepción base del dominio"""
    pass

class ProfesorNoVerificadoException(DomainException):
    """El profesor no está verificado"""
    pass

class GrupoNoEncontradoException(DomainException):
    """Grupo no registrado o no encontrado"""
    pass

class RecaudacionException(DomainException):
    """Error en proceso de recaudación"""
    pass

class AIException(DomainException):
    """Error al comunicarse con la IA"""
    pass
