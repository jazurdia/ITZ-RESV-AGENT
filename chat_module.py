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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user",   "content": userQuery}
            ],
            max_tokens=2000,
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
        "Contexto del negocio:\n"
        f"{itzana_knowledge}\n\n"
        "Intenta siempre relacionar los datos con el contexto del negocio. Al responder es desable que complementes con informacion del contexto de negocio, pero no es obligatorio.\n\n"
        "Por favor, responde en formato Markdown siguiendo estas secciones si es adecuado:\n\n"
        "1. **Título**\n"
        "   - Debe ser breve, claro y representativo del análisis.\n\n"
        "   - El titulo no es 'titulo', sino que debes generar un titulo descriptivo de la respuesta.\n"
        "2. **Análisis**\n"
        "   - Comenta tendencias, anomalías, contexto, oportunidades y riesgos.\n"
        "   - Adapta el lenguaje al estilo conversacional; evita formatos rígidos.\n\n"
        "3. **Datos**\n"
        "   - Si los datos de `returned_json` son relevantes, incluye la tabla completa.\n"
        "   - Asegúrate de:\n"
        "     • Formatear números con comas para miles y punto para decimales.\n"
        "   - Moneda: USD si aplica (revenue siempre en dólares).\n"
        "   - Si no son útiles, omite esta sección.\n\n"    
        "   - Si hay una celda en la tabla que esta vacia, no incluyas esa fila en la tabla.\n"
        "4. **Gráfica**\n"
        "   - Si recibes `graph_url`, incrusta la imagen justo después de la tabla.\n"
        "   - Si no hay URL, omite esta sección.\n\n"
        "   - Si no hay url, nisiquiera menciones la grafica.\n"
        "5. **Recomendaciones**\n"
        "   - Usa la informacion del contexto de negocio y los datos analizados."
        "   - Bullet points con acciones realistas para el día a día del resort.\n"
        "   - Solo inclúyelas si los datos permiten sugerir algo útil.\n\n"
        "   - Extiendete en esta seccion, pero no repitas lo que ya has dicho en el análisis.\n"
        "6. \n"
        "   - Recuerda que solo usaste la información proporcionada.\n"
        "   - Mantén siempre un tono cercano y conversacional.\n\n"
        "— No inventes nada: usa únicamente la información disponible."
    )


    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
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
    

async def chat_evaluate_questions(user_question:str) -> str:
    """
    Evalua la pregunta del usuario para determinar si es adecuada para el analisis de datos, o debe ser consultada en la web. 
    """

    prompt = (
        "Tu tarea es evaluar la pregunta del usuario y determinar si es adecuada para el agente del analisis de datos y su worflow, "
        "o si puede ser contestada con una busqueda en la web. "

    )