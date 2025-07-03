import base64
import io
import json
import sqlite3
from typing import Any, Dict, List
from typing_extensions import TypedDict, NotRequired
from matplotlib import pyplot as plt
import pandas as pd
from pydantic import BaseModel
from agents import Agent, function_tool, AgentOutputSchema
from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

from typing_extensions import TypedDict

#########################################################
##############  ANALISIS DE RESERVACIONES  ##############
#########################################################

class AnalysisOutput(TypedDict):
    """
    Esquema de salida estricto:
    - returned_json: lista de objetos con los resultados de la consulta
    - interpretation: texto con la interpretación
    """
    returned_json: List[Dict[str, Any]]
    interpretation: str
    userQuery: str



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
- `userQuery`: la pregunta original del usuario. 

Devolver únicamente un objeto JSON válido con este esquema:
   {{
     "returned_json": [...],
     "interpretation": "...",
     "userQuery: "..."
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

#########################################################
##############      Agente Graficador      ##############
#########################################################
class GraphOutput(TypedDict):
    returned_json: List[Dict[str, Any]]
    interpretation: str
    userQuery: str
    imgb64: str


@function_tool(strict_json_schema=False)
def generate_graphs(
    data: List[Dict[str, Any]],
    chart_type: str,
    x: str,
    y: str = ""
) -> str:
    df = pd.DataFrame(data)
    chart_type = chart_type.lower()
    
    plt.figure(figsize=(10, 6))
    try:
        if chart_type == "bar":
            plt.bar(df[x], df[y])
        elif chart_type == "line":
            df[x] = pd.to_datetime(df[x], errors='ignore')
            df = df.sort_values(by=x)
            plt.plot(df[x], df[y], marker='o')
            plt.xticks(rotation=45)
        elif chart_type == "pie":
            plt.pie(df[y], labels=df[x], autopct='%1.1f%%')
        else:
            return ""
    except Exception:
        return ""

    plt.title(f"{chart_type.capitalize()} Chart: {y} by {x}")
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    img_b64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    return img_b64

graph_generator_instructions = """
Eres un agente que genera gráficos a partir de datos tabulares.
Recibes tres cosas: 
- `returned_json`: una tabla de datos (lista de diccionarios con claves como columnas)
- `interpretation`: una explicación en texto de esos datos
- `userQuery`: la pregunta original del usuario

Tu tarea es:
1. Analizar los datos y la pregunta.
2. Elegir el tipo de gráfico más adecuado: "bar", "line", "pie", etc.
3. Elegir las columnas `x` e `y` apropiadas del `returned_json`.
4. Llamar a la herramienta `generate_graphs`, pasándole directamente:
   - `data`: el valor de `returned_json`
   - `chart_type`: el tipo de gráfico a generar (ej: "bar", "line", "pie")
   - `x`: nombre de la columna para el eje X
   - `y`: nombre de la columna para el eje Y (si aplica; puede estar vacío en pie charts)

5. Devuelve como resultado final un objeto JSON con la siguiente forma:

{
  "returned_json": [...],
  "interpretation": "...",
  "userQuery": "...",
  "imgb64": "..."  # gráfico codificado en base64
}

No escribas explicaciones adicionales. No escribas código Python. Solo devuelve el objeto JSON con esos campos.
"""



graph_generator_agent = Agent(
    name="Graph Generator Agent",
    instructions=graph_generator_instructions,
    model="gpt-4.1",
    tools=[generate_graphs],
    output_type=AgentOutputSchema(GraphOutput, strict_json_schema=False)
)


#########################################################
##############      Agente Coordinador     ##############
#########################################################

GRAPH_KEYWORDS = ["grafica", "gráfico", "gráfica", "visualiza", "visualización", "diagrama", "imagen", "representa"]

class FinalOutput(TypedDict):
    returned_json: List[Dict[str, Any]]
    interpretation: str
    userQuery: str
    imgb64: NotRequired[str]

coordinator_instructions = """
Eres un agente coordinador. Tu tarea es recibir la pregunta del usuario y decidir qué agentes deben intervenir.

1. Siempre debes comenzar usando `handoff` con el `ReservationsAgent`, pasándole directamente la pregunta del usuario.

2. Una vez recibas la respuesta (un JSON con los campos `returned_json`, `interpretation`, `userQuery`), analiza si la `userQuery` contiene alguna de estas palabras clave:
   - "gráfico", "gráfica", "grafica", "visualiza", "visualización", "diagrama", "imagen", "representa"

3. Si contiene alguna de esas palabras, haz un segundo `handoff`, esta vez al `Graph Generator Agent`, y pásale el mismo JSON.

4. Devuelve como resultado final un objeto JSON con los campos:
   - `returned_json`
   - `interpretation`
   - `userQuery`
   - `imgb64` (solo si se pidió un gráfico; si no, este campo puede omitirse)

Nunca generes gráficos ni SQL por tu cuenta. Usa `handoff`.
"""


coordinator_agent = Agent(
    name="CoordinatorAgent",
    instructions=coordinator_instructions,
    model="gpt-4.1",
    tools=[],
    allowed_agents=[reservations_agent, graph_generator_agent],
    output_type=AgentOutputSchema(FinalOutput, strict_json_schema=False)
)




