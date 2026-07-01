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