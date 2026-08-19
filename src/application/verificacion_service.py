import unicodedata
from typing import List, Dict

def normalizar_texto(texto: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin caracteres especiales"""
    if not texto:
        return ""
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.category(c).startswith('M'))


def _extraer_primer_palabra(texto: str) -> str:
    """Extrae y normaliza la primera palabra de un texto"""
    partes = (texto or '').strip().split()
    return normalizar_texto(partes[0]) if partes else ''


def leer_excel_estudiantes(file_path: str) -> List[Dict[str, str]]:
    """Lee un archivo Excel y retorna lista de estudiantes como dicts.
    
    Columnas esperadas: Cédula, Apellidos, Nombres, Correo
    """
    try:
        import openpyxl
    except ImportError:
        raise ValueError("La librería 'openpyxl' no está instalada en el servidor. Instálala ejecutando: pip install openpyxl")

    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb.active
    
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    
    if not rows:
        raise ValueError("El archivo Excel está vacío.")
    
    # Map normalized header names to column indices
    header_row = rows[0]
    col_map = {}
    for i, h in enumerate(header_row):
        if h and str(h).strip():
            key_norm = normalizar_texto(str(h))
            col_map[key_norm] = i
    
    # Validate required columns (normalized)
    columnas_requeridas = {
        'cedula': 'CÉDULA',
        'apellidos': 'APELLIDOS',
        'nombres': 'NOMBRES',
        'correo': 'CORREO'
    }
    
    faltantes = [nombre_orig for key_norm, nombre_orig in columnas_requeridas.items() if key_norm not in col_map]
    if faltantes:
        raise ValueError(
            f"Columna(s) no encontrada(s): {', '.join(faltantes)}\n"
            f"Columnas encontradas en Excel: {', '.join(str(h) for h in header_row if h)}"
        )
    
    estudiantes = []
    for row in rows[1:]:
        if not row or all(cell is None for cell in row):
            continue
        
        cedula = str(row[col_map['cedula']] or '').strip() if col_map['cedula'] < len(row) else ''
        apellidos = str(row[col_map['apellidos']] or '').strip() if col_map['apellidos'] < len(row) else ''
        nombres = str(row[col_map['nombres']] or '').strip() if col_map['nombres'] < len(row) else ''
        correo = str(row[col_map['correo']] or '').strip() if col_map['correo'] < len(row) else ''
        
        # Skip empty rows
        if not cedula and not apellidos and not nombres:
            continue
        
        estudiantes.append({
            'cedula': cedula,
            'apellidos': apellidos,
            'nombres': nombres,
            'correo': correo
        })
    
    return estudiantes


def verificar_miembros(estudiantes_grupo, miembros_telegram):
    """Compara la lista de estudiantes contra los miembros de Telegram.
    
    Comparación dual: primer_nombre+primer_apellido Y primer_apellido+primer_nombre
    para cubrir nombres invertidos en Telegram.
    
    Args:
        estudiantes_grupo: Lista de tuples (cedula, apellidos, nombres, correo)
                          o lista de dicts con claves 'apellidos' y 'nombres'
        miembros_telegram: Lista de tuples (user_id, first_name, last_name, username)
    
    Returns:
        (verificados, no_registrados): dos listas de tuples de miembros
    """
    # Build set of (primer_nombre, primer_apellido) pairs from student list
    excel_pares = set()
    for est in estudiantes_grupo:
        if isinstance(est, (list, tuple)):
            apellidos = est[1] or ''
            nombres = est[2] or ''
        else:
            apellidos = est.get('apellidos', '')
            nombres = est.get('nombres', '')
        
        primer_apellido = _extraer_primer_palabra(apellidos)
        primer_nombre = _extraer_primer_palabra(nombres)
        
        if primer_apellido and primer_nombre:
            excel_pares.add((primer_nombre, primer_apellido))
    
    verificados = []
    no_registrados = []
    
    for miembro in miembros_telegram:
        user_id, first_name, last_name, username = miembro
        
        fn = _extraer_primer_palabra(first_name)
        ln = _extraer_primer_palabra(last_name)
        
        # Dual check: normal (nombre, apellido) and inverted (apellido, nombre)
        match_normal = (fn, ln) in excel_pares if fn and ln else False
        match_invertido = (ln, fn) in excel_pares if fn and ln else False
        
        if match_normal or match_invertido:
            verificados.append(miembro)
        else:
            no_registrados.append(miembro)
    
    return verificados, no_registrados
