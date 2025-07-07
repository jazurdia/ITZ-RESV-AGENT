from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ItzanaAgents import reservations_agent
from load_xlsx_to_sqlite import (
    load_reservations_to_sqlite,
    load_grouped_accounts_to_sqlite,
    delete_itzana_db
)
from agents import Runner
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import List, Dict, Any

import json
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder




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
    lifespan=lifespan
)

class output_ask(BaseModel):
    returned_json: List[Dict[str, Any]]
    key_findings: str
    methodology: str
    results_interpretation: str
    conclusion: str

@app.post("/ask", summary="Pregunta al agente.", response_model=output_ask)
async def query_agent(request: QueryRequest):
    """
    Recibe un JSON con el campo 'question' y devuelve la respuesta estructurada del agente.
    """
    try:
        resultado = await Runner.run(reservations_agent, request.question)

        raw = resultado.final_output

        output = jsonable_encoder(raw)

        if isinstance(output, str):
            output = json.loads(output)

        return JSONResponse(content=output)

        
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