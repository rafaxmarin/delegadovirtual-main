import tempfile
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def generar_word_apa(contenido: str) -> str:
    """Genera un documento Word con formato APA 7ma edición (UNIDADES CORREGIDAS CON Pt e Inches)"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
    
    doc = Document()
    
    # Configurar márgenes (1 pulgada = 2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
    
    # Estilo APA
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)  # Corregido: Pt(12) en lugar de entero raw 152400
    style.paragraph_format.line_spacing = 2.0
    style.paragraph_format.first_line_indent = Inches(0.5)  # Corregido: Inches(0.5) en lugar de entero raw 914400
    
    lineas = contenido.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if linea:
            paragraph = doc.add_paragraph(linea)
            if linea.isupper() or len(linea) < 60:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if paragraph.runs:
                    paragraph.runs[0].bold = True
    
    doc.save(temp_file.name)
    return temp_file.name
