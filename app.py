from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ItzanaAgents import reservations_agent, graph_decider_agent
from load_xlsx_to_sqlite import (
    load_reservations_to_sqlite,
    load_grouped_accounts_to_sqlite,
    delete_itzana_db
)
from agents import Runner
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from helper import _generate_graphs_impl

import json
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from helper import format_as_markdown

import traceback


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
    # lifespan=lifespan
)

class OutputAsk(BaseModel): # creo que ya no se usa. 
    title: str
    returned_json: List[Dict[str, Any]]
    key_findings: str
    methodology: str
    results_interpretation: str
    recommendations: str
    conclusion: str
    imgb64: Optional[str] = None

class outputAsk2(BaseModel):
    markdown : str


GRAPH_KEYWORDS = [
    "grafica", "gráfico", "gráfica",
    "grafico", "visualiza", "visualización",
    "diagrama", "imagen", "representa"
]

@app.post("/ask", response_model=outputAsk2)
async def query_agent(request: QueryRequest):
    try:
        # 1) Llamas al agente SQL
        resp = await Runner.run(reservations_agent, request.question)
        raw: Dict[str, Any] = resp.final_output  # dict con your analysis

        try: 
            # 2) Si pide gráfico, decides parámetros
            if any(k in request.question.lower() for k in GRAPH_KEYWORDS):
                data_json = json.dumps(raw["returned_json"])
                # 3) Invoca al agente decidor (siempre recibe un STRING)
                payload = json.dumps({"data_json": data_json, "userQuery": request.question})
                dec = await Runner.run(graph_decider_agent, payload)
                choice: Dict[str, str] = dec.final_output

                # 4) Generas la gráfica tú mismo
                raw["imgb64"] = _generate_graphs_impl(
                    raw["returned_json"],
                    choice["chart_type"],
                    choice["x"],
                    choice["y"]
                )

        except Exception as e:
            print("no se pudo generar la imagen. ")
            raw["imgb64"] = None

        # 3. Formatear como Markdown
        md = format_as_markdown(
            title = raw["title"],
            resp={"returned_json": raw["returned_json"]},
            key_findings=raw["key_findings"],
            methodology=raw["methodology"],
            interpretation=raw["results_interpretation"],
            recommendations = raw["recommendations"],
            conclusion=raw["conclusion"],
            imgb64=raw.get("imgb64")
        )

        # 4. Devolver solo el Markdown como JSON
        return outputAsk2(markdown=md)

    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "traceback": tb}
        )


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