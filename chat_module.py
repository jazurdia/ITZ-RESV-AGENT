import asyncio
import json
from openai import OpenAI

from helper import load_context

from dotenv import load_dotenv
import os

# Carga variables de entorno desde .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Falta definir OPENAI_API_KEY en las variables de entorno")

client = OpenAI(api_key=OPENAI_API_KEY)

resv_columns = load_context("knowledge/reservations_columns.md")
wholesalers_list = load_context("knowledge/wholesalers.txt")
itzana_knowledge = load_context("knowledge/itzana_context.md")

async def chat_betterQuestions(userQuery: str) -> str:
    """
    Genera una versión mejorada de la pregunta original para que sea
    más clara y específica al ejecutarse contra la base de datos.
    """
    contexto = (
        "Eres un asistente experto en análisis de datos para el resort Itz'ana. "
        "Tu tarea es transformar la pregunta del usuario en una instrucción técnica, concisa y precisa, describiendo EXACTAMENTE la consulta a realizar, usando los nombres exactos de las columnas de la tabla 'reservations'. "
        "Corrige cualquier error ortográfico en los nombres de mayoristas (wholesalers) usando la lista de mayoristas conocidos. "
        "Si el usuario menciona un mayorista de forma incorrecta o con errores, corrígelo y usa el nombre correcto. "
        "No generes el query SQL. "
        "No seas conversacional, solo describe con precisión qué columnas se deben usar para agrupar, filtrar, sumar, contar, etc. No contestes preguntas. "
        "IMPORTANTE: Si parte de la pregunta del usuario solicita recomendaciones o preguntas abiertas que no se pueden responder con datos, debes devolver esa parte ademas de lo referente a la consulta sql. "
        "No repitas la pregunta original. "
        "Ejemplo: 'Obtener el total de EFFECTIVE_RATE_AMOUNT agrupado por ROOM_CATEGORY_LABEL, filtrando por COMPANY_NAME igual a \"EXPEDIA, INC.\".' "
        f"Columnas de la tabla: {resv_columns} "
        f"Lista de mayoristas: {wholesalers_list} "
        "Si la pregunta menciona una grafica y no menciona el tipo de grafica, asume que es una barra."
        "Si la pregunta menciona una grafica y menciona el tipo de grafica, usa ese tipo. pero intenta mejorar la descripcion de la grafica."
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
        f"Contexto del negocio:\n{itzana_knowledge}\n\n"
        "Por favor, responde en formato Markdown siguiendo estas pautas:\n\n"
        "1. **Título**: Comienza con un título breve y relevante para el análisis.\n"
        "2. **Análisis libre**: Explica con tus palabras lo más relevante de los datos, "
        "puedes incluir tendencias, anomalías, contexto, oportunidades, riesgos, etc. "
        "No sigas un formato rígido, adapta el análisis a lo que veas en los datos.\n"
        "3. **Tabla de datos**: Incluye la tabla completa, con todos los datos presentes en returned_json. Si los datos no son relevantes, omite esta sección. Si lo son, muestra TODA la tabla. \n"
        "   Considera que si los datos son de revenue, estan siempre en dolares americanos (USD).\n Agregalo a la tabla. "
        "   Corrige el formato de los numeros, con comas como separador de miles y punto como separador decimal. "
        "3.5 **Gráfica**: Si el agente generó una gráfica, incluye la imagen con la URL proporcionada en `graph_url`. "
        "4. **Recomendaciones**: Propón acciones concretas y prácticas basadas en los datos, "
        "adaptadas al día a día del resort. Que sean claras, realistas y directamente aplicables. Solo haz esto si la data es suficiente para que sea útil. Deben ser bulletpoints. Si no, omite esta sección. \n"
        "5. Termina con un recordatorio de que solo se usó la información proporcionada y mantén siempre el tono cercano.\n\n"
        "No inventes nada: usa únicamente la información proporcionada."

    )

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(agent_response, indent=2) if isinstance(agent_response, dict) else agent_response}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al generar respuesta conversacional: {e}")
        return f"No se pudo generar la respuesta conversacional. {agent_response} "