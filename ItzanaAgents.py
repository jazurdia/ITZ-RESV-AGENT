import json
import sqlite3
from typing import Any
from openai import BaseModel
from agents import Agent, Runner, function_tool, handoffs
from load_xlsx_to_sqlite import reservations_schema, groupedaccounts_schema

class analysis_output(BaseModel):
    returned_json: Any    # JSON de resultados (lista de filas o dict)
    interpretation: str   # Interpretación en lenguaje natural de esos resultados

class response_output(BaseModel):
    title: str
    explanation: str
    tabular_result: str
    insights: str
    summary: str

response_instructions = """
Eres el agente de respuesta final. Tu misión es tomar la información tabular en formato JSON `returned_json` y la interpretación `interpretation` dadas por otros agentes, y convertirlas en texto amigable para el usuario.

Debes presentar la información de `returned_json` como una tabla en la respuesta final (usa formato Markdown para la tabla si es necesario). **No inventes información**: si `returned_json` contiene un mensaje de error o notificación, muéstralo tal cual en la tabla.

Tu respuesta **debe** tener el siguiente formato JSON, rellenando cada campo adecuadamente:
- `title`: Un título breve para los resultados presentados.
- `explanation`: Una explicación o análisis en español utilizando la interpretación proporcionada.
- `tabular_result`: Los datos de `returned_json` formateados como tabla.
- `insights`: Insights o conclusiones adicionales que se puedan obtener de los datos.
- `summary`: Un resumen final de los resultados y conclusiones.
"""

response_agent = Agent(
    name="ResponseAgent",
    instructions=response_instructions,
    model="gpt-4.1",             
    output_type=response_output        # la salida debe seguir la estructura definida en response_output
)

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
"""

reservations_agent = Agent(
    name="ReservationsAgent",
    instructions=reservations_instructions,
    model="gpt-4.1",
    tools=[execute_query_to_sqlite],       # herramienta para ejecutar consultas SQL
    output_type=analysis_output,           # espera devolver returned_json e interpretation
    handoffs=[response_agent]              # puede delegar en ResponseAgent para formatear la respuesta
)

# Instrucciones del agente de análisis de cuentas agrupadas
accounts_instructions = f"""
Eres un analista de datos con acceso a la base SQLite `Itzana.db`. La tabla principal es `groupedaccounts`.
El esquema de la tabla `groupedaccounts` es el siguiente: {groupedaccounts_schema()}.

Tu tarea es, según la pregunta del usuario, **generar una consulta SQL** sobre la tabla `groupedaccounts` para obtener la información solicitada. Asegúrate de usar las columnas correctas según el esquema proporcionado.

Luego ejecuta la consulta con la herramienta `execute_query_to_sqlite` para obtener los resultados en JSON, y responde con un JSON que contenga:
- `returned_json`: los datos obtenidos de la consulta.
- `interpretation`: una explicación en español de esos datos o la respuesta concreta a la pregunta basada en los datos.

Recuerda que si la pregunta implica análisis numérico o de ingresos/egresos financieros, esta tabla puede contener la información relevante.

Al final, delega la respuesta al agente de formato usando `transfer_to_ResponseAgent` para que genere la respuesta final al usuario.
"""

accounts_agent = Agent(
    name="AccountsAgent",
    instructions=accounts_instructions,
    model="gpt-3.5-turbo",
    tools=[execute_query_to_sqlite],
    output_type=analysis_output,
    handoffs=[response_agent]
)

@function_tool
def search_internet(query: str) -> str:
    """Simula una búsqueda en Internet devolviendo un mensaje (herramienta a implementar en el futuro)."""
    # Nota: En una implementación real, aquí se haría una petición a un buscador o API.
    return f"(Resultado de búsqueda no disponible para '{query}')"


# Instrucciones del agente coordinador
coordinator_instructions = """
Eres un **agente coordinador** cuya función es recibir la pregunta del usuario y decidir cómo resolverla coordinando a otros agentes especializados. 
Formas parte del sistema de consultas de datos de *Itzana Resorts*.

Sigue estas reglas:
- Debes pasarle la pregunta al agente `reservations_agent`. 

Tu objetivo es entender la intención del usuario y encaminar la resolución de la pregunta de la manera adecuada, usando los agentes o herramientas disponibles. **No intentes responder con suposiciones sin datos**; para datos, apóyate en los agentes correspondientes.
"""

coordinator_agent = Agent(
    name="Coordinator",
    instructions=coordinator_instructions,
    model="gpt-4.1",  # Ejemplo: usar un modelo más potente para coordinación y entendimiento general
    tools=[],
    # El coordinador puede delegar solo a los agentes de análisis (no directamente al de respuesta):
    handoffs=[reservations_agent]
)