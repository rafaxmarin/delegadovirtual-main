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

def generar_pdf_reporte_recaudacion(datos_rec: dict, pagos: list) -> str:
    """Genera un reporte formal en PDF con la tabla detallada de pagos y referencias bancarias"""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    doc = SimpleDocTemplate(
        temp_file.name,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1A365D')
    )
    
    subtitulo_style = ParagraphStyle(
        'SubtituloDoc',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4A5568')
    )

    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2D3748')
    )

    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1A202C')
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.white
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    story = []
    
    # 1. ENCABEZADO
    story.append(Paragraph("<b>CONTROL Y REPORTE OFICIAL DE RECAUDACIÓN</b>", titulo_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Grupo:</b> {datos_rec.get('nombre_grupo', 'General')} | <b>Fecha de Emisión:</b> {datos_rec.get('fecha_generacion', '')}", subtitulo_style))
    story.append(Spacer(1, 14))

    # 2. CUADRO DE METADATOS DE LA RECAUDACIÓN
    concepto = datos_rec.get('concepto', '')
    monto_u = float(datos_rec.get('monto_unitario', 0.0))
    total_rec = float(datos_rec.get('total_recaudado', 0.0))
    cant_est = int(datos_rec.get('cant_estudiantes', 0))
    banco = datos_rec.get('banco', '')
    estado = datos_rec.get('estado', 'Activa')
    fecha_limite = datos_rec.get('fecha_limite', '')

    resumen_data = [
        [
            Paragraph("<b>Concepto:</b>", meta_label), Paragraph(concepto, meta_val),
            Paragraph("<b>Estado:</b>", meta_label), Paragraph(estado, meta_val)
        ],
        [
            Paragraph("<b>Monto / Estudiante:</b>", meta_label), Paragraph(f"Bs. {monto_u:,.2f}", meta_val),
            Paragraph("<b>Banco Destino:</b>", meta_label), Paragraph(banco, meta_val)
        ],
        [
            Paragraph("<b>Total Recaudado:</b>", meta_label), Paragraph(f"<b>Bs. {total_rec:,.2f}</b>", meta_val),
            Paragraph("<b>Total Pagos:</b>", meta_label), Paragraph(f"{cant_est} estudiante(s)", meta_val)
        ],
        [
            Paragraph("<b>Fecha Límite:</b>", meta_label), Paragraph(fecha_limite, meta_val),
            Paragraph("", meta_label), Paragraph("", meta_val)
        ]
    ]

    t_resumen = Table(resumen_data, colWidths=[100, 170, 90, 180])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 14))

    # 3. TABLA DETALLADA DE ESTUDIANTES Y PAGOS
    story.append(Paragraph("<b>DETALLE DE PAGOS REGISTRADOS Y CONCILIACIÓN</b>", meta_label))
    story.append(Spacer(1, 6))

    table_data = [
        [
            Paragraph("<b>#</b>", th_style),
            Paragraph("<b>Estudiante Registrado</b>", th_style),
            Paragraph("<b>N° Referencia</b>", th_style),
            Paragraph("<b>Reportado Por (Telegram)</b>", th_style),
            Paragraph("<b>Cédula</b>", th_style),
            Paragraph("<b>Fecha / Hora</b>", th_style)
        ]
    ]

    if pagos:
        for idx, p in enumerate(pagos, start=1):
            nombre_est = p[0] or ''
            fecha_p = p[1] or ''
            num_ref = p[3] or 'S/R'
            rep_nom = p[5] if len(p) > 5 and p[5] else nombre_est
            rep_ced = p[6] if len(p) > 6 and p[6] else 'N/A'

            table_data.append([
                Paragraph(str(idx), td_style),
                Paragraph(nombre_est, td_bold),
                Paragraph(str(num_ref), td_bold),
                Paragraph(str(rep_nom), td_style),
                Paragraph(str(rep_ced), td_style),
                Paragraph(str(fecha_p), td_style)
            ])
    else:
        table_data.append([
            Paragraph("—", td_style),
            Paragraph("<i>Ningún pago registrado aún</i>", td_style),
            Paragraph("—", td_style),
            Paragraph("—", td_style),
            Paragraph("—", td_style),
            Paragraph("—", td_style)
        ])

    col_widths = [25, 140, 105, 125, 65, 80]
    t_pagos = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    # Alternar color de filas
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')))

    t_pagos.setStyle(TableStyle(t_style))
    story.append(t_pagos)

    doc.build(story)
    return temp_file.name
