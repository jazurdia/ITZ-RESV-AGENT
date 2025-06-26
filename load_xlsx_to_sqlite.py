import pandas as pd
import os
import sqlite3

def load_reservations_to_sqlite(xlsx_path: str, db_path: str = "Itzana.db", table_name: str = "reservations"):
    """
    Lee un archivo XLSX y vuelca su contenido en SQLite:
      - xlsx_path: ruta al archivo .xlsx
      - db_path: nombre (o ruta) de la base SQLite
      - table_name: nombre de la tabla a crear/reemplazar
    """
    # Carga el Excel
    df = pd.read_excel(xlsx_path)
    # Conecta (o crea) la base de datos
    conn = sqlite3.connect(db_path)
    # Inserta el DataFrame en la tabla indicada
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return len(df)  # devuelve número de registros cargados

def load_grouped_accounts_to_sqlite(xlsx_path: str, db_path: str = "Itzana.db", table_name: str = "groupedaccounts"):
    """
    Lee un archivo XLSX y vuelca su contenido en SQLite:
      - xlsx_path: ruta al archivo .xlsx
      - db_path: nombre (o ruta) de la base SQLite
      - table_name: nombre de la tabla a crear/reemplazar
    """
    # Carga el Excel
    df = pd.read_excel(xlsx_path)
    # Conecta (o crea) la base de datos
    conn = sqlite3.connect(db_path)
    # Inserta el DataFrame en la tabla indicada
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return len(df)  # devuelve número de registros cargados

def delete_itzana_db(db_path: str = "Itzana.db") -> bool:
    """
    Elimina el fichero de la base de datos SQLite.
    
    Args:
      db_path: Ruta al fichero .db (por defecto, "Itzana.db" en el directorio de trabajo).
      
    Returns:
      True si el fichero existía y fue borrado, False si no existía.
    """
    if os.path.isfile(db_path):
        os.remove(db_path)
        print(f"✅ {db_path} eliminado.")
        return True
    else:
        print(f"ℹ️  No se encontró {db_path}. Nada que borrar.")
        return False
    
# Implementación de funciones para obtener el esquema de las tablas:
def reservations_schema(db_path: str = "Itzana.db", table_name: str = "reservations") -> str:
    """Devuelve un string con las columnas y tipos de la tabla `reservations` de Itzana.db."""
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

def groupedaccounts_schema(db_path: str = "Itzana.db", table_name: str = "groupedaccounts") -> str:
    """Devuelve un string con las columnas y tipos de la tabla `groupedaccounts` de Itzana.db."""
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
    col_defs = [f"{col[1]} ({col[2]})" for col in cols]
    return ", ".join(col_defs)