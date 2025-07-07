import json
import sqlite3
from typing import Any, List, Dict
from pydantic import BaseModel
from agents import Agent, function_tool, AgentOutputSchema
from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

from typing_extensions import TypedDict

class AnalysisOutput(TypedDict):
    """
    Esquema de salida estricto:
    - returned_json: lista de objetos con los resultados de la consulta
    - interpretation: texto con la interpretación
    """
    returned_json: List[Dict[str, Any]]
    interpretation: str


@function_tool
def execute_query_to_sqlite(query: str) -> Any:
    """Ejecuta la consulta SQL en Itzana.db y retorna resultados."""
    conn = None
    try:
        conn = sqlite3.connect("Itzana.db")
        cursor = conn.cursor()
        cursor.execute(query)
        if query.strip().lower().startswith("select"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        else:
            conn.commit()
            result = [{"mensaje": f"Consulta ejecutada. Filas afectadas: {cursor.rowcount}"}]
        return result
    except Exception as e:
        return [{"error": f"Error al ejecutar la consulta: {str(e)}"}]
    finally:
        if conn:
            conn.close()

# Instrucciones para el agente de reservaciones
reservations_instructions = f"""
Eres un analista de datos con acceso a una base SQLite llamada `Itzana.db`. La tabla principal es `reservations`.
El esquema de la tabla `reservations` es el siguiente: {reservations_schema()}.

Tu tarea es, a partir de la pregunta del usuario, **generar una consulta SQL (SQLite)** sobre la tabla `reservations` que permita responder a la pregunta. Debes razonar qué datos solicitar.

Una vez generada la consulta, úsala llamando a la herramienta `execute_query_to_sqlite` para obtener los datos en formato JSON. **Luego, debes entregar tu respuesta en un JSON con dos campos**:
- `returned_json`: el resultado devuelto por la consulta (en JSON).
- `interpretation`: una interpretación en texto de ese `returned_json` (qué significan los datos o la respuesta a la pregunta del usuario).

Devolver únicamente un objeto JSON válido con este esquema:
   {{
     "returned_json": [...],
     "interpretation": "..."
   }}

NOTAS:
- Si la pregunta menciona wholesalers, debes usar el campo COMPANY_NAME.
- Sin explicación adicional ni código; solo produce el objeto JSON con los campos `returned_json` e `interpretation`.
"""

reservations_agent = Agent(
    name="ReservationsAgent",
    instructions=reservations_instructions,
    model="gpt-4.1",
    tools=[execute_query_to_sqlite],
    output_type=AgentOutputSchema(AnalysisOutput, strict_json_schema=False)

)
