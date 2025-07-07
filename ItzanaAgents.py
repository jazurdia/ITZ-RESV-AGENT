import base64
import io
import sqlite3
from typing import Any, Dict, List

from typing_extensions import TypedDict, NotRequired

import pandas as pd
from matplotlib import pyplot as plt

from agents import Agent, function_tool, AgentOutputSchema, handoff
from agents.tool import FunctionTool

from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema


# Esquema que permite cualquier columna adicional en cada fila de “data”
raw_schema = {
  "type": "object",
  "additionalProperties": False,
  "properties": {
    "data":       {"type": "array", "items": {"type": "object", "additionalProperties": True}},
    "chart_type": {"type": "string"},
    "x":          {"type": "string"},
    "y":          {"type": "string"}
  },
  # ahora incluimos todas las keys, incluidas "y"
  "required": ["data", "chart_type", "x", "y"]
}

params_schema = raw_schema


# Convertimos en esquema “estricto” para el SDK, pero dejando additionalProperties = true



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

def _generate_graphs_impl(
    data_json: str,
    chart_type: str,
    x: str,
    y: str = ""
) -> str:
    # 1) parsea el JSON string
    data = pd.json.loads(data_json)
    # 2) procede con la misma lógica:
    df = pd.DataFrame(data)
    ct = chart_type.lower()
    plt.figure(figsize=(10,6))
    if ct == "bar":
        plt.bar(df[x], df[y])
    elif ct == "line":
        df[x] = pd.to_datetime(df[x], errors="ignore")
        df = df.sort_values(by=x)
        plt.plot(df[x], df[y], marker="o")
        plt.xticks(rotation=45)
    elif ct == "pie":
        plt.pie(df[y], labels=df[x], autopct="%1.1f%%")
    plt.title(f"{ct.capitalize()} Chart: {y} by {x}")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return img

generate_graphs_tool = FunctionTool(
    name="generate_graphs",
    description="Genera un gráfico PNG en base64 a partir de un string JSON de datos tabulares.",
    params_json_schema=params_schema,
    on_invoke_tool=lambda _ctx, args: _generate_graphs_impl(
        args["data_json"],
        args["chart_type"],
        args["x"],
        args.get("y", "")
    )
)


graph_generator_instructions = """
Eres un agente especializado en generar gráficos a partir de datos tabulares. Recibes tres entradas:
- `returned_json`: una lista de diccionarios con los datos de la consulta.
- `interpretation`: una explicación en texto de lo que significan esos datos.
- `userQuery`: la pregunta original del usuario.

Tu flujo de trabajo debe ser:

1. Preparar el payload serializando `returned_json` a JSON:
   data_json = json.dumps(returned_json)

2. Elegir el gráfico más adecuado según la pregunta y los datos:
   - chart_type: "bar", "line" o "pie"
   - x: columna para el eje X
   - y: columna para el eje Y (o "" si no aplica)

3. Invocar la herramienta:
   generate_graphs(
     data_json=data_json,
     chart_type=chart_type,
     x=x,
     y=y
   )

4. Formar la respuesta devolviendo exclusivamente un objeto JSON con:
{
  "returned_json": returned_json,
  "interpretation": interpretation,
  "userQuery": userQuery,
  "imgb64": imgb64
}

No escribas explicaciones adicionales ni código Python; solo devuelve ese JSON.
"""



graph_generator_agent = Agent(
    name="Graph Generator Agent",
    instructions=graph_generator_instructions,
    model="gpt-4.1",
    tools=[generate_graphs_tool],               # ← aquí
    output_type=AgentOutputSchema(GraphOutput, strict_json_schema=False)
)



#########################################################
##############      Agente Coordinador     ##############
#########################################################

# Palabras clave para petición de gráfico
GRAPH_KEYWORDS = [
    "grafica", "gráfico", "gráfica",
    "visualiza", "visualización",
    "diagrama", "imagen", "representa"
]

class FinalOutput(TypedDict):
    returned_json: List[Dict[str, Any]]
    interpretation: str
    userQuery: str
    imgb64: NotRequired[str]  # Solo si hay gráfico

coordinator_instructions = f"""
Eres un agente coordinador. Tu única tarea es delegar mediante las funciones automáticas transfer_to_*:

1. Primero emite:
{{"assistant": "transfer_to_ReservationsAgent", "input": userQuery}}

2. Si la pregunta contiene alguna de estas palabras clave: {GRAPH_KEYWORDS}, inmediatamente después emite:
{{"assistant": "transfer_to_GraphGeneratorAgent", "input": <resultado del primer handoff>}}

3. Finalmente, devuelve solo la salida del último handoff realizado (sin texto adicional).
"""


coordinator_agent = Agent(
    name="CoordinatorAgent",
    instructions=coordinator_instructions,
    model="gpt-4.1",
    tools=[],
    handoffs=[
        reservations_agent.as_tool(tool_name="Reservation Analyzer", tool_description="performs a sql query over the database and analyzes the result"), 
        graph_generator_agent.as_tool(tool_name="Graphicator", tool_description="creates graphics given the result of Reservation Analyzer")
        ],
    output_type=AgentOutputSchema(FinalOutput, strict_json_schema=False)
)