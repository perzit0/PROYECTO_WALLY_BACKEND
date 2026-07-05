import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


def exportar_historial_excel(lecturas, device_id):
    """
    Recibe una lista de objetos Lectura y genera un archivo Excel en memoria.
    Retorna un objeto BytesIO listo para enviarse con send_file.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial"

    headers = ["ID", "Device ID", "CO (ppm)", "MQ135", "PM (µg/m³)", "Latitud", "Longitud", "Fecha"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num, _ in enumerate(headers, 1):
        celda = ws.cell(row=1, column=col_num)
        celda.fill = header_fill
        celda.font = header_font
        celda.alignment = Alignment(horizontal="center")

    for lectura in lecturas:
        ws.append([
            lectura.id,
            lectura.device_id,
            lectura.co if lectura.co is not None else "S/D",
            lectura.mq135 if lectura.mq135 is not None else "S/D",
            lectura.pm if lectura.pm is not None else "S/D",
            lectura.lat if lectura.lat is not None else "S/D",
            lectura.lng if lectura.lng is not None else "S/D",
            lectura.timestamp.strftime("%Y-%m-%d %H:%M:%S") if lectura.timestamp else "S/D",
        ])

    for columna in ws.columns:
        max_len = max(len(str(c.value)) if c.value else 0 for c in columna)
        ws.column_dimensions[columna[0].column_letter].width = max_len + 4

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def exportar_monitoreo_excel(monitoreo, lecturas):
    """Genera un Excel con dos hojas: Resumen (métricas del monitoreo zonal)
    y Recorrido (cada punto GPS + sensores registrados durante la sesión)."""
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    # --- Hoja Resumen ---
    ws_resumen = wb.active
    ws_resumen.title = "Resumen"

    duracion_min = None
    if monitoreo.hora_fin and monitoreo.hora_inicio:
        duracion_min = round((monitoreo.hora_fin - monitoreo.hora_inicio).total_seconds() / 60, 1)

    filas_resumen = [
        ("Robot (device_id)", monitoreo.device_id),
        ("Nombre del monitoreo", monitoreo.nombre or "S/D"),
        ("Estado", monitoreo.estado),
        ("Hora de inicio", monitoreo.hora_inicio.strftime("%Y-%m-%d %H:%M:%S") if monitoreo.hora_inicio else "S/D"),
        ("Hora de fin", monitoreo.hora_fin.strftime("%Y-%m-%d %H:%M:%S") if monitoreo.hora_fin else "S/D"),
        ("Duración (minutos)", duracion_min if duracion_min is not None else "S/D"),
        ("Ubicación de inicio", f"{monitoreo.lat_inicio}, {monitoreo.lng_inicio}" if monitoreo.lat_inicio else "S/D"),
        ("Ubicación de fin", f"{monitoreo.lat_fin}, {monitoreo.lng_fin}" if monitoreo.lat_fin else "S/D"),
        ("Promedio CO (ppm)", monitoreo.promedio_co if monitoreo.promedio_co is not None else "S/D"),
        ("Promedio MQ135", monitoreo.promedio_mq135 if monitoreo.promedio_mq135 is not None else "S/D"),
        ("Promedio PM (µg/m³)", monitoreo.promedio_pm if monitoreo.promedio_pm is not None else "S/D"),
        ("Nivel de calidad de aire", monitoreo.nivel_color or "S/D"),
        ("Centro de la zona (lat, lng)", f"{monitoreo.centro_lat}, {monitoreo.centro_lng}" if monitoreo.centro_lat else "S/D"),
        ("Radio de la zona (metros)", monitoreo.radio_metros if monitoreo.radio_metros is not None else "S/D"),
        ("Distancia total recorrida (m)", monitoreo.distancia_total_m if monitoreo.distancia_total_m is not None else "S/D"),
        ("Velocidad promedio (km/h)", monitoreo.velocidad_promedio_kmh if monitoreo.velocidad_promedio_kmh is not None else "S/D"),
        ("Total de puntos registrados", monitoreo.total_puntos or 0),
    ]

    ws_resumen.cell(row=1, column=1, value="Reporte de Monitoreo Zonal - WALLY").font = Font(bold=True, size=14, color="1F4E78")
    ws_resumen.merge_cells("A1:B1")

    for i, (etiqueta, valor) in enumerate(filas_resumen, start=3):
        celda_etiqueta = ws_resumen.cell(row=i, column=1, value=etiqueta)
        celda_etiqueta.font = Font(bold=True)
        ws_resumen.cell(row=i, column=2, value=valor)

    ws_resumen.column_dimensions["A"].width = 32
    ws_resumen.column_dimensions["B"].width = 40

    # --- Hoja Recorrido ---
    ws_rec = wb.create_sheet("Recorrido")
    headers = ["#", "Latitud", "Longitud", "GPS interpolado", "CO (ppm)", "MQ135", "PM (µg/m³)", "Velocidad (km/h)", "Fecha/Hora"]
    ws_rec.append(headers)
    for col_num, _ in enumerate(headers, 1):
        celda = ws_rec.cell(row=1, column=col_num)
        celda.fill = header_fill
        celda.font = header_font
        celda.alignment = Alignment(horizontal="center")

    for idx, l in enumerate(lecturas, start=1):
        ws_rec.append([
            idx,
            l.lat if l.lat is not None else "S/D",
            l.lng if l.lng is not None else "S/D",
            "Sí" if l.gps_interpolado else "No",
            l.co if l.co is not None else "S/D",
            l.mq135 if l.mq135 is not None else "S/D",
            l.pm if l.pm is not None else "S/D",
            l.velocidad_kmh if l.velocidad_kmh is not None else "S/D",
            l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "S/D",
        ])

    for columna in ws_rec.columns:
        max_len = max(len(str(c.value)) if c.value else 0 for c in columna)
        ws_rec.column_dimensions[columna[0].column_letter].width = max_len + 4

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def exportar_usuarios_excel(usuarios):
    """
    Recibe una lista de objetos Usuario y genera un Excel con el listado.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Usuarios"

    headers = ["ID", "Nombre", "Email", "Rol", "Verificado", "Creado en"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num, _ in enumerate(headers, 1):
        celda = ws.cell(row=1, column=col_num)
        celda.fill = header_fill
        celda.font = header_font
        celda.alignment = Alignment(horizontal="center")

    for u in usuarios:
        ws.append([
            u.id,
            u.nombre,
            u.email,
            u.rol,
            "Sí" if u.email_verificado else "No",
            u.creado_en.strftime("%Y-%m-%d %H:%M:%S") if u.creado_en else "S/D",
        ])

    for columna in ws.columns:
        max_len = max(len(str(c.value)) if c.value else 0 for c in columna)
        ws.column_dimensions[columna[0].column_letter].width = max_len + 4

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer