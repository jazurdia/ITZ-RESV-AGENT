from fastapi import FastAPI, HTTPException
from httpcore import request
from pydantic import BaseModel
from ItzanaAgents import reservations_agent
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

import logging
from openai import OpenAI

from chat_module import chat_betterQuestions, chat_better_answers

from aux_scripts.config import OPENAI_API_KEY

load_dotenv()  # Carga las variables de entorno desde .env

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

class QueryRequest(BaseModel):
    question: str


app = FastAPI(
    title="Itzana Agents API",
    description="API para ejecutar los agentes de análisis (currently 1)",
    version="1.0.0",
)

class outputAsk(BaseModel): # creo que ya no se usa. 
    title: str
    returned_json: List[Dict[str, Any]]
    findings: str
    methodology: str
    #results_interpretation: str
    #recommendations: str
    #conclusion: str
    #url_img: Optional[str] = None
    better_answers: str

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

        print(f"[DEBUG] - Pregunta recibida: {request.question}")

        better_question = await chat_betterQuestions(request.question)
        
        print(f"[DEBUG] - Pregunta mejorada: {better_question}")

        print(f"[INFO] - Iniciando el agente de reservaciones")
        # 1) Llamas al agente SQL
        resp = await Runner.run(reservations_agent, better_question)
        raw: Dict[str, Any] = resp.final_output  # dict con your analysis
        print(f"[DEBUG] - Respuesta del agente de reservaciones: \n------------------------\n{json.dumps(raw, ensure_ascii=False)} \n------------------------\n")

        betterAnswers = await chat_better_answers(raw)

        print(f"\n[DEBUG] - Respuesta mejorada: \n------------------------\n\n{betterAnswers}")

        return {"markdown" : betterAnswers}
        

    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "traceback": tb}
        )



if __name__ == "__main__":
    # Ejecutar con: python app.py o uvicorn app:app --reload --host 0.0.0.0 --port 8000
    import uvicorn
    # Levanta la app desde este módulo (app.py)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

# http://127.0.0.1:8000/docs