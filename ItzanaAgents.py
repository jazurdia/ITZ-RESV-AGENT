import json
import sqlite3
from typing import Any
from openai import BaseModel
from agents import Agent, Runner, function_tool, handoffs
from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

class analysis_output(BaseModel):
    returned_json: str    # JSON de resultados (lista de filas o dict)
    interpretation: str   # Interpretación en lenguaje natural de esos resultados


@function_tool
def execute_query_to_sqlite(query: str) -> Any:
    """Ejecuta la consulta SQL proporcionada en Itzana.db y devuelve los resultados en formato JSON."""

    print(f"Query > {query}")

    conn = None
    try:
        conn = sqlite3.connect("Itzana.db")
        cursor = conn.cursor()
        cursor.execute(query)  # Ejecutar la consulta
        # Si la consulta es SELECT, obtener los resultados:
        if query.strip().lower().startswith("select"):
            columns = [desc[0] for desc in cursor.description]  # nombres de columnas
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]  # lista de diccionarios
        else:
            # Si no es SELECT (por ejemplo, UPDATE), devolver filas afectadas
            conn.commit()
            result = [{"mensaje": f"Consulta ejecutada. Filas afectadas: {cursor.rowcount}"}]
        return result
    except Exception as e:
        error_msg = str(e)
        # Devolver un JSON con mensaje de error
        return [{"error": f"Error al ejecutar la consulta: {error_msg}"}]
    finally:
        if conn:
            conn.close()

# Instrucciones del agente de análisis de reservaciones
reservations_instructions = f"""
Eres un analista de datos con acceso a una base SQLite llamada `Itzana.db`. La tabla principal es `reservations`. 
El esquema de la tabla `reservations` es el siguiente: {reservations_schema()}.

Tu tarea es, a partir de la pregunta del usuario, **generar una consulta SQL (SQLite)** sobre la tabla `reservations` que permita responder a la pregunta. Debes razonar qué datos solicitar.

Una vez generada la consulta, úsala llamando a la herramienta `execute_query_to_sqlite` para obtener los datos en formato JSON. **Luego, debes entregar tu respuesta en un JSON con dos campos**:
- `returned_json`: el resultado devuelto por la consulta (en JSON).
- `interpretation`: una interpretación en texto de ese `returned_json` (qué significan los datos o la respuesta a la pregunta del usuario).

NOTAS:
- Si la pregunta menciona wholesalers, debes usar el campo COMPANY_NAME. 
"""

reservations_agent = Agent(
    name="ReservationsAgent",
    instructions=reservations_instructions,
    model="gpt-4.1",
    tools=[execute_query_to_sqlite],       # herramienta para ejecutar consultas SQL
    output_type=str,           # espera devolver returned_json e interpretation
)



