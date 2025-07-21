import os
import io
import random
import string
import requests

from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import sqlite3

# para cargar archivos de knowledge
def load_context(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

# Implementación de funciones para obtener el esquema de las tablas:
def reservations_schema(db_path: str = "../resv.db", table_name: str = "reservations") -> str:
    """Devuelve un string con las columnas y tipos de la tabla `reservations` de resv.db."""
    if not os.path.isfile(db_path):
        return "(Esquema no disponible: base de datos no encontrada)"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = cur.fetchall()
    except Exception as e:
        conn.close()
        return "(Esquema no disponible: error al leer la tabla)"
    conn.close()
    if not cols:
        return "(Tabla vacía o no encontrada)"
    # Formatear las columnas como "nombre (TIPO)" separadas por comas
    col_defs = [f"{col[1]} ({col[2]})" for col in cols]  # col[1]=nombre, col[2]=tipo
    return ", ".join(col_defs)

def upload_to_file_server(file_path: str = None, buf: io.BytesIO = None) -> str:
    """
    Sube un archivo (desde ruta local o buffer) al servidor y devuelve la URL pública.
    """

    # Genera nombre único
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rand_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=3))
    filename = f"{timestamp}-{rand_suffix}.png"

    # Decide fuente de datos
    if buf is not None:
        file_data = (filename, buf, "image/png")
    elif file_path is not None:
        with open(file_path, "rb") as f:
            file_data = (filename, f, "image/png")
    else:
        raise ValueError("Debes proporcionar file_path o buf")

    resp = requests.post(
        "https://agents.garooinc.com/upload",
        files={"file": file_data}
    )
    resp.raise_for_status()
    result = resp.json()

    if resp.status_code == 200 and result.get("success", True):
        url_img = "https://agents.garooinc.com/files/" + filename
        return url_img
    else:
        raise Exception(f"Error al subir el archivo: {result.get('error', 'Unknown error')}")
    

def execute_graph_agent_code(code: str, table_data: list, output_file:str = "out.png") -> str:
    """
    Executes python code generated from the graph_code_agent and uploads the resulting image to the file server.
    """
    img_buf = io.BytesIO()

    code = code.replace("plt.show()", "")

    exec_globals = {
        "table_data": table_data,
        "pd": pd,
        "plt": plt,
        "img_buf": img_buf
    }

    print(f"[DEBUG] - Ejecutando código del agente de gráficos:\n{code}")
    try:
        exec(code, exec_globals)
    except Exception as e:
        raise RuntimeError(f"Error al ejecutar el código del agente de gráficos: {e}")
    
    if img_buf.getbuffer().nbytes == 0:
        raise ValueError("El código del agente de gráficos no generó una imagen válida.")
    
    public_url = upload_to_file_server(buf=img_buf)
    print(f"[DEBUG] - Imagen subida correctamente: {public_url}")
    return public_url

