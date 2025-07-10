import json
from typing import Any, List, Dict, Optional

import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

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

    # 5) Guardar en buffer y codificar a base64
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()

    return img_b64

import json



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
    img = _generate_graphs_impl(table, ct, x, y)

    # 5) Devolver solo los campos necesarios
    return {
        "returned_json": table,
        "userQuery":     userQuery,
        "imgb64":        img
    }

def format_as_markdown(
    title: str,
    resp: Dict[str, Any],
    key_findings: str,
    methodology: str,
    interpretation: str,
    recommendations: str,
    conclusion: str,
    imgb64: Optional[str] = None
) -> str:
    # 0) Título principal
    md = f"# {title}\n\n"

    # 1) Tabla dinámica para returned_json
    rows = resp.get("returned_json", [])
    if rows and isinstance(rows, list):
        headers = list(rows[0].keys())
        md += "## Datos\n\n"
        md += "|" + "|".join(headers) + "|\n"
        md += "|" + "|".join("---" for _ in headers) + "|\n"
        for row in rows:
            cells = ["" if row.get(h) is None else str(row[h]) for h in headers]
            md += "|" + "|".join(cells) + "|\n"
        md += "\n"
    else:
        md += "_No hay datos en returned_json_\n\n"

    # 2) Secciones de texto
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

    # 3) Imagen embebida (si existe)
    if imgb64:
        md += "## Gráfica\n\n"
        md += f"![Gráfico](data:image/png;base64,{imgb64})\n"

    return md

