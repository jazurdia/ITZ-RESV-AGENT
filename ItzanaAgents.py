import json
import sqlite3
from typing import Any, List, Dict, TypedDict
from pydantic import BaseModel
from agents import Agent, function_tool, AgentOutputSchema
from agents.tool import FunctionTool
from agents.tool import CodeInterpreterTool

from data_processing.load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

from helper import _graph_all_in_one_impl, graph_tool_schema

from typing_extensions import TypedDict

from aux_scripts.contexto import string_contexto

# ----------------------------------
#         Analysis Agent 
# ----------------------------------

class AnalysisOutput(TypedDict):
    """
    Esquema de salida estricto:
    - title: titulo de la respuesta. 
    - returned_json: lista de objetos con los resultados de la consulta
    - findings: resumen de los hallazgos principales
    - methodology: descripción del proceso y filtros aplicados
    """
    title: str
    returned_json: List[Dict[str, Any]]
    findings: str
    methodology: str
    #results_interpretation: str
    #recommendations: str
    #conclusion: str

@function_tool
def execute_query_to_sqlite(query: str) -> Any:
    """Ejecuta la consulta SQL en Itzana.db y retorna resultados."""
    conn = None

    print(f"[DEBUG] - Consulta SQL generada por el agente:\n{query}")  # <-- Agrega este print

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

Una vez generada la consulta, úsala llamando a la herramienta `execute_query_to_sqlite` para obtener los datos en formato JSON. **Luego, debes entregar tu respuesta en un JSON con los siguientes campos**:

- `title`: un título descriptivo de la respuesta.
- `returned_json`: el resultado devuelto por la consulta (en JSON).
- `findings`: explicacion de los datos encontrados.
- `methodology`: descripción de cómo se generó la consulta y qué filtros se aplicaron.

Devuelve **solo** un objeto JSON válido con este esquema:

{{
  "title": "Título descriptivo de la respuesta",
  "returned_json": [...],
  "findings": "...",
  "methodology": "..."
}}

NOTAS:
- Si la pregunta menciona wholesalers, debes usar el campo COMPANY_NAME.
- No uses nunca los nombres de las columnas como respuestas, debes adaptar este nombre a un lenguaje conversacional. 
- Responde en el lenguaje de la pregunta. 
- las unidades monetarias son en USD.
- toda la informacion de la tabla `reservations` es del resort Itzana. Por lo que no vale la pena incluirlo al hacer consultas. 
- en otras palabras, no uses WHERE RESORT = 'Itz''ana'. 

"""

reservations_agent = Agent(
    name="ReservationsAgent",
    instructions=reservations_instructions,
    model="gpt-4o",
    tools=[execute_query_to_sqlite],
    output_type=AgentOutputSchema(AnalysisOutput, strict_json_schema=False)

)

# ----------------------------------
#       Graph Generator Agent
# ----------------------------------

# So far... this is what I have. https://chatgpt.com/share/6879f4c5-38e8-8007-9584-437fe067a02d



