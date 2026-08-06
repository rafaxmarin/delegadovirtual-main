import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def generar_pdf_apa(contenido: str) -> str:
    """Genera un PDF con formato APA 7ma edición"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    doc = SimpleDocTemplate(
        temp_file.name,
        pagesize=letter,
        rightMargin=72,  # 1 pulgada
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    estilo_apa = ParagraphStyle(
        'APA',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=24,  # Doble espacio
        alignment=TA_JUSTIFY,
        firstLineIndent=36  # Sangría primera línea
    )
    
    estilo_titulo = ParagraphStyle(
        'TituloAPA',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        alignment=TA_CENTER,
        leading=24
    )
    
    elementos = []
    lineas = contenido.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if linea:
            if linea.isupper() or len(linea) < 60:
                elementos.append(Paragraph(linea, estilo_titulo))
            else:
                elementos.append(Paragraph(linea, estilo_apa))
            elementos.append(Spacer(1, 12))
    
    doc.build(elementos)
    return temp_file.name
