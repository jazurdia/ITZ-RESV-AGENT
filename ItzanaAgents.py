import json
import sqlite3
from typing import Any, List, Dict
from pydantic import BaseModel
from agents import Agent, function_tool, AgentOutputSchema
from agents.tool import FunctionTool
from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

from helper import _graph_all_in_one_impl, graph_tool_schema

from typing_extensions import TypedDict

# ----------------------------------
#         Analysis Agent 
# ----------------------------------

class AnalysisOutput(TypedDict):
    """
    Esquema de salida estricto:
    - title: titulo de la respuesta. 
    - returned_json: lista de objetos con los resultados de la consulta
    - key_findings: resumen de los hallazgos principales
    - methodology: descripción del proceso y filtros aplicados
    - results_interpretation: interpretación de lo que significan los datos
    - recommendations: acciones recomendadas de acuerdo con la pregunta y los datos extraidos.
    - conclusion: conclusiones y próximos pasos
    """
    title: str
    returned_json: List[Dict[str, Any]]
    key_findings: str
    methodology: str
    results_interpretation: str
    recommendations: str
    conclusion: str

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

Una vez generada la consulta, úsala llamando a la herramienta `execute_query_to_sqlite` para obtener los datos en formato JSON. **Luego, debes entregar tu respuesta en un JSON con los siguientes campos**:

- `title`: un nombre para la respuesta. 
- `returned_json`: el resultado devuelto por la consulta (en JSON).
- `methodology`: descripción del proceso, filtros o agregaciones aplicados sin mencionar nombres de columna. 
- `results_interpretation`: interpretación de lo que significan los datos en el contexto de negocio. Debe ser extenso. 
- `key_findings`: resumen de los hallazgos principales extraídos de `returned_json`.
- `recommendations`: genera recomendaciones 
- `conclusion`: conclusiones y próximos pasos sugeridos.

Devuelve **solo** un objeto JSON válido con este esquema:

{{
  "title": "..."
  "returned_json": [...],
  "key_findings": "...",
  "methodology": "...",
  "results_interpretation": "...",
  "recommendations": "..."
  "conclusion": "..."
}}

NOTAS:
- Si la pregunta menciona wholesalers, debes usar el campo COMPANY_NAME.
- No uses nunca los nombres de las columnas como respuestas, debes adaptar este nombre a un lenguaje conversacional. 

"""

reservations_agent = Agent(
    name="ReservationsAgent",
    instructions=reservations_instructions,
    model="gpt-4.1",
    tools=[execute_query_to_sqlite],
    output_type=AgentOutputSchema(AnalysisOutput, strict_json_schema=False)

)

# ----------------------------------
#       Graphicator Agent 
# ----------------------------------

# --- Esquema de salida para la decisión ---
class GraphChoice(TypedDict):
    chart_type: str
    x: str
    y: str

# --- El único FunctionTool: decide_chart_type_xy ---
@function_tool
def decide_graph(data_json: str, userQuery: str) -> GraphChoice:
    """
    data_json: JSON-string de returned_json (la tabla).
    userQuery: la pregunta original.
    Devuelve un JSON con chart_type, x, y.
    """
    table = json.loads(data_json)
    first = table[0] if table else {}
    q = userQuery.lower()

    # 1) Tipo de gráfico
    if "line" in q or "tendencia" in q:
        ct = "line"
    elif "pie" in q or "%" in q or "torta" in q:
        ct = "pie"
    else:
        ct = "bar"

    # 2) Eje X: primer campo de texto
    text_cols = [k for k,v in first.items() if isinstance(v, str)]
    x = text_cols[0] if text_cols else next(iter(first), "")

    # 3) Eje Y: primer campo numérico distinto de X
    y = ""
    for k,v in first.items():
        if k != x and isinstance(v, (int, float)):
            y = k
            break

    return {"chart_type": ct, "x": x, "y": y}

# --- Agente que usa sólo ese tool ---
graph_decider_instructions = """
Eres un agente que decide el tipo de gráfico y los ejes.
Recibes dos parámetros:
- data_json: un string JSON con la lista returned_json.
- userQuery: la pregunta original.

Debes invocar la herramienta decide_graph con esos dos parámetros
y devolver únicamente su salida (el JSON con chart_type, x, y).
"""


graph_decider_agent = Agent(
    name="GraphDeciderAgent",
    instructions=graph_decider_instructions,
    model="gpt-4.1",
    tools=[decide_graph],
    output_type=AgentOutputSchema(GraphChoice, strict_json_schema=False)
)