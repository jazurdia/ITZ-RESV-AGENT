# chat_module.py

import os
import asyncio
from openai import OpenAI
from load_xlsx_to_sqlite import reservations_schema

from aux_scripts.contexto import string_contexto

# Instancia del cliente OpenAI (versión >=1.0.0)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def chat_betterQuestions(userQuery: str) -> str:
    """
    Genera una versión mejorada de la pregunta original para que sea
    más clara y específica al ejecutarse contra la base de datos.
    """
    contexto = (
        "Eres un asistente experto en análisis de datos para el resort Itz'ana. "
        "Tu tarea es mejorar la pregunta del usuario para que sea clara, precisa y fácil de responder "
        "por un agente de datos. SOLO puedes usar la información disponible en la tabla 'reservations', cuyo esquema es: "
        f"{reservations_schema()}. "
        "No agregues detalles ni pidas información que no esté en este esquema. "
        "No pidas análisis avanzados, solo consultas directas, filtros y agrupaciones posibles con los campos disponibles. "
        "Incluye detalles relevantes en la pregunta mejorada, como canal, compañía, montos, fechas, tipo de habitación, y cualquier filtro útil, "
        "pero solo si existen en el esquema. "
        "Si la pregunta menciona 'wholesaler' o 'wholesalers', debes usar el campo COMPANY_NAME. "
        "No inventes datos ni relaciones. "
        "Mejora la redacción y especificidad de la consulta original, pero limita la pregunta a lo que realmente puede responderse con los datos y campos existentes."
    )

    try:
        # Ejecutamos la llamada síncrona en un hilo para no bloquear el event loop
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user",   "content": userQuery}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al generar preguntas: {e}")
        # Si algo falla, devolvemos la pregunta original
        return userQuery


async def chat_better_answers(agent_response: dict) -> str:
    """
    Genera una respuesta conversacional y profesional en formato Markdown
    a partir de la respuesta estructurada del agente.
    """
    # chat_module.py (o donde definas tu prompt)

    prompt = (
        "Eres un compañero experto en análisis de datos para el resort Itz'ana en Placencia, Belice, "
        "con un estilo conversacional, como si estuviéramos charlando sobre los números.\n\n"
        f"Contexto del negocio:\n{string_contexto}\n\n"
        f"Lo que devolvió el agente:\n{agent_response}\n\n"
        "Por favor, responde en formato Markdown siguiendo estas pautas:\n\n"
        "1. **Título**: Comienza con un título breve y relevante para el análisis.\n"
        "2. **Análisis libre**: Explica con tus palabras lo más relevante de los datos, "
        "puedes incluir tendencias, anomalías, contexto, oportunidades, riesgos, etc. "
        "No sigas un formato rígido, adapta el análisis a lo que veas en los datos.\n"
        "3. **Tabla de datos**: Incluye la tabla completa tal como la devolvió el agente si es relevante. Si no, omite esta sección.\n"
        "4. **Recomendaciones**: Propón acciones concretas y prácticas basadas en los datos, "
        "adaptadas al día a día del resort. Que sean claras, realistas y directamente aplicables. Solo haz esto si la data es suficiente para que sea útil. Si no, omite esta sección. \n"
        "5. **Cierre**: Termina con un recordatorio de que solo se usó la información proporcionada y mantén siempre el tono cercano.\n\n"
        "No inventes nada: usa únicamente la información proporcionada."
    )

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de datos y redacción profesional para el resort Itz'ana."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al generar respuesta conversacional: {e}")
        return f"No se pudo generar la respuesta conversacional. {agent_response} "