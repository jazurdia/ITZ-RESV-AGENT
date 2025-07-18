from datetime import datetime
import json
import random
import string
from typing import Any, List, Dict, Optional

import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import json


def _generate_graphs_impl(
    data: List[Dict[str, Any]],
    chart_type: str,
    x: str,
    y: str = ""
) -> str:
    """
    data: lista de diccionarios con tus filas de returned_json
    chart_type: "bar", "line" o "pie"
    x: nombre de la columna para el eje X
    y: nombre de la columna para el eje Y (puede quedar "")
    
    Devuelve un PNG codificado en Base64.
    """

    print(f"[DEBUG] - Iniciando herramienta de graficacion")
    print(f"[DEBUG] - Los parametros recibidos son los siguientes: \n\tTipo: {chart_type} \n\tx: {x} \n\ty: {y}")

    # 1) Cargar los datos en un DataFrame
    df = pd.DataFrame(data)

    # Filtrar filas con valores nulos en x o y
    df = df[df[x].notnull() & df[y].notnull()]

    # 2) Preparar figura
    plt.figure(figsize=(10, 6))
    ct = chart_type.lower()

    # 3) Dibujar según el tipo
    if ct == "bar":
        plt.bar(df[x], df[y])
        plt.xlabel(x)
        plt.ylabel(y)
        plt.xticks(rotation=45)
    elif ct == "line":
        # Asegurarse de que x sea datetime si corresponde
        try:
            df[x] = pd.to_datetime(df[x])
        except Exception:
            pass
        df = df.sort_values(by=x)
        plt.plot(df[x], df[y], marker="o")
        plt.xlabel(x)
        plt.ylabel(y)
        plt.xticks(rotation=45)
    elif ct == "pie":
        plt.pie(df[y], labels=df[x], autopct="%1.1f%%")
    else:
        # Si el tipo no es soportado, devolvemos cadena vacía
        print(f"[DEBUG] - El tipo de la herramienta no es soportado. ")
        return ""

    # 4) Título y ajustes
    plt.title(f"{ct.capitalize()} Chart: {y} by {x}")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    # 5) Generar nombre único: YYYYMMDD-HHMMSS-XYZ.png
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rand_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=3))
    filename = f"{timestamp}-{rand_suffix}.png"

    # 6) Subir la imagen
    resp = requests.post(
        "https://agents.garooinc.com/upload",
        files={"file": (filename, buf, "image/png")}
    )
    resp.raise_for_status()
    result = resp.json()

    # Verifica que el servidor confirme la subida y devuelva la URL
    if resp.status_code == 200 and result.get("success", True):
        url_img = "https://agents.garooinc.com/files/" + filename
        return url_img
    else:
        print(f"[DEBUG] - Falló la subida de la imagen: {result}")
        return ""


# JSON-Schema que solo acepta strings para evitar validación de objetos anidados
graph_tool_schema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "returned_json": {"type": "string"},  # aquí metemos json.dumps(returned_json)
        "userQuery": {"type": "string"}
    },
    "required": ["returned_json", "userQuery"]
}

def _graph_all_in_one_impl(returned_json: str, userQuery: str) -> Dict[str, Any]:
    # 1) Deserializar la tabla
    table = json.loads(returned_json)

    # 2) Decidir tipo de gráfico
    q = userQuery.lower()
    if "line" in q or "tendencia" in q:
        ct = "line"
    elif "pie" in q or "%" in q or "torta" in q:
        ct = "pie"
    else:
        ct = "bar"

    # 3) Elegir ejes X/Y
    first = table[0] if table else {}
    text_cols = [k for k,v in first.items() if isinstance(v, str)]
    x = text_cols[0] if text_cols else next(iter(first), "")
    y = ""
    for k,v in first.items():
        if k != x and isinstance(v, (int, float)):
            y = k
            break

    # 4) Generar la imagen
    url_img = _generate_graphs_impl(table, ct, x, y)

    # 5) Devolver solo los campos necesarios
    return {
        "url_img":        url_img
    }

def format_as_markdown(
    title: str,
    resp: Dict[str, Any],
    key_findings: str,
    methodology: str,
    interpretation: str,
    recommendations: str,
    conclusion: str,
    url_img: Optional[str] = None
) -> str:
    md = f"# {title}\n\n"

    rows = resp.get("returned_json", [])
    if rows and isinstance(rows, list):
        headers = list(rows[0].keys())
        md += "## Datos\n\n"
        md += "|" + "|".join(headers) + "|\n"
        md += "|" + "|".join("---" for _ in headers) + "|\n"
        for row in rows:
            cells = []
            for h in headers:
                val = row.get(h)
                if val is None:
                    cells.append("")
                elif isinstance(val, (int, float)):
                    # Formato correcto: coma miles, punto decimal
                    cells.append(f"{val:,.2f}")
                else:
                    cells.append(str(val))
            md += "|" + "|".join(cells) + "|\n"
        md += "\n"
    else:
        md += "_No hay datos en returned_json_\n\n"

    md += "## Hallazgos clave\n\n"
    md += key_findings + "\n\n"

    md += "## Metodología\n\n"
    md += methodology + "\n\n"

    md += "## Interpretación de resultados\n\n"
    md += interpretation + "\n\n"

    md += "## Recomendaciones\n\n"
    md += recommendations + "\n\n"

    md += "## Conclusión\n\n"
    md += conclusion + "\n\n"

    if url_img:
        md += "## Gráfica\n\n"
        md += f"![Gráfico]({url_img})\n"

    return md

