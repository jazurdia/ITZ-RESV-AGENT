from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ItzanaAgents import reservations_agent, graph_generator_agent
from load_xlsx_to_sqlite import (
    load_reservations_to_sqlite,
    load_grouped_accounts_to_sqlite,
    delete_itzana_db
)
from agents import Runner
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import json, ast

load_dotenv()

class QueryRequest(BaseModel):
    question: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Limpiar y cargar la base de datos al iniciar la API
    delete_itzana_db()
    load_reservations_to_sqlite("data/reservations.xlsx")
    load_grouped_accounts_to_sqlite("data/grouped_accounts.xlsx")
    yield

app = FastAPI(
    title="Itzana Agents API",
    description="API para ejecutar los agentes de análisis (currently 1)",
    version="1.0.0",
    #lifespan=lifespan
)

@app.post("/ask", summary="Pregunta al agente.")
async def query_agent(request: QueryRequest):

    """
    Recibe una pregunta del usuario, y el agente coordinador decide:
    - Ejecutar la consulta SQL con el agente de reservaciones
    - Opcionalmente generar un gráfico si la pregunta lo solicita

    Devuelve:
    - `returned_json`
    - `interpretation`
    - `userQuery`
    - `imgb64` (solo si aplica)
    """

    try:
        # resultado = await Runner.run(coordinator_agent, request.question)
        # return resultado.final_output

        # primero se llama al analisis. 
        analisis = await Runner.run(reservations_agent, request.question)
        raw = analisis.final_output

        # si contiene alguna de las keyword, llamar al segundo agente. 
        GRAPH_KEYWORDS = [
            "grafica", "gráfico", "gráfica", "grafico",
            "visualiza", "visualización",
            "diagrama", "imagen", "representa"
        ]

        # 2. Detectar si el usuario pidió gráfico
        pregunta = request.question.lower()
        if any(k in pregunta for k in GRAPH_KEYWORDS):

            payload = json.dumps(raw)

            # 3. Llamar al agente gráfico pasándole directamente el dict
            grafico = await Runner.run(
                graph_generator_agent,
                payload  # graph_generator_agent espera un dict con keys returned_json, interpretation, userQuery
            )

            wawa = grafico
            
            debug = 10+10

    except Exception as e:
        # Captura errores de ejecución del agente y devuelve un HTTP 500 con detalle
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.post("/reload", summary="Recarga la base de datos desde los archivos XLSX")
async def reload_db():
    delete_itzana_db()
    reservas = load_reservations_to_sqlite("data/reservations.xlsx")
    cuentas = load_grouped_accounts_to_sqlite("data/grouped_accounts.xlsx")
    return {"reservations_loaded": reservas, "accounts_loaded": cuentas}

if __name__ == "__main__":
    # Ejecutar con: python app.py o uvicorn app:app --reload --host 0.0.0.0 --port 8000
    import uvicorn
    # Levanta la app desde este módulo (app.py)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

# http://127.0.0.1:8000/docs