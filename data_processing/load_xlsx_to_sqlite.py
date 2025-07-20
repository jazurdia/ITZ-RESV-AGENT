import pandas as pd
import os
import sqlite3
    
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

