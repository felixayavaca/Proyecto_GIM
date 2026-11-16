from io import BytesIO
from itertools import chain

from flask import send_file
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from routers.router_login import requiere_permiso


@requiere_permiso('reportes.exportar')
def generar_excel(nombre_archivo, encabezados, filas):
    """Genera una descarga desde una vista Flask; protege también la vista si consulta datos."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = 'Reporte'
    anchos = {}
    negrita = Font(bold=True)

    for numero_fila, valores in enumerate(chain((encabezados,), filas), start=1):
        for columna, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=numero_fila, column=columna, value=valor)
            if isinstance(valor, str):
                celda.data_type = 's'  # Exportar el texto literal, incluso si empieza con '='.
            if numero_fila == 1:
                celda.font = negrita
            largo = max((len(linea) for linea in str(valor).splitlines()), default=0) if valor is not None else 0
            anchos[columna] = max(anchos.get(columna, 0), largo)

    for columna, ancho in anchos.items():
        hoja.column_dimensions[get_column_letter(columna)].width = min(255, max(10, ancho + 2))

    if not nombre_archivo.lower().endswith('.xlsx'):
        nombre_archivo += '.xlsx'

    contenido = BytesIO()
    libro.save(contenido)
    contenido.seek(0)
    return send_file(
        contenido,
        download_name=nombre_archivo,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
