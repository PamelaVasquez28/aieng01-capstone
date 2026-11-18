"""
H3: Evals del revisor de Declaraciones de Origen.

Ejecuta:
    python evals.py                           # todos los casos, con guardrails
    python evals.py --sin-guardrails          # sin guardrails
    python evals.py --etiqueta antes          # guarda resultados/antes.json
    python evals.py --comparar antes despues  # diferencias
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

AQUI = Path(__file__).parent
DIR_RESULTADOS = AQUI / "resultados"

JUEZ_SCHEMA = {
    "type": "object",
    "properties": {"razon": {"type": "string"}, "cumple": {"type": "boolean"}},
    "required": ["razon", "cumple"],
    "additionalProperties": False,
}
JUEZ_SYSTEM = (
    "Eres un evaluador estricto de un revisor de Declaraciones de Origen. "
    "Recibes la pregunta, la respuesta del agente y UNA rúbrica. "
    "Decide solo si la respuesta cumple; no evalúes estilo. "
    "Responde: primero la razón (1-2 frases), luego el veredicto."
)


def cargar_golden(ruta: Path = AQUI / "golden_set.json") -> list[dict]:
    return json.loads(ruta.read_text(encoding="utf-8"))["casos"]


# ── Calificadores por código ────────────────────────────────────────────────
def calificar_codigo(espera: dict, resultado: dict) -> list[tuple[str, bool, str]]:
    """Retorna [(calificador, pasó, detalle)]."""
    salida = []
    herramientas = resultado.get("herramientas_usadas", [])
    resp = resultado.get("respuesta", "").lower()
    bloqueado = resultado.get("rechazado", False)

    # Herramientas requeridas
    for h in espera.get("herramientas", []):
        h_short = h.replace("mcp__aduana__", "")
        matches = any(h_short in herr for herr in herramientas)
        salida.append((f"usa {h_short}", matches, f"llamó {herramientas}"))

    # Herramientas prohibidas
    prohibidas = espera.get("sin_herramientas", [])
    if prohibidas == ["*"]:
        salida.append(("no usa herramientas", not herramientas, f"llamó {herramientas}"))
    else:
        for h in prohibidas:
            h_short = h.replace("mcp__aduana__", "")
            matches = any(h_short in herr for herr in herramientas)
            salida.append((f"no usa {h_short}", not matches, f"llamó {herramientas}"))

    # Texto que debe contener alguno
    if espera.get("contiene_alguno"):
        hay = [t for t in espera["contiene_alguno"] if t.lower() in resp]
        salida.append(("menciona lo esperado", bool(hay), f"buscó {espera['contiene_alguno']}, encontró {hay}"))

    # Texto que no debe contener
    for t in espera.get("no_contiene", []):
        no_tiene = t.lower() not in resp
        salida.append((f"no dice «{t}»", no_tiene, ""))

    # Guardrail de entrada
    if "bloqueado_entrada" in espera:
        debe_bloquear = espera["bloqueado_entrada"]
        ok = bloqueado == debe_bloquear
        salida.append(("guardrail entrada", ok, f"bloqueado={bloqueado}, esperaba={debe_bloquear}"))

    return salida


# ── Calificador por modelo ────────────────────────────────────────────────
def juez(pregunta: str, respuesta: str, rubrica: str) -> tuple[bool, str]:
    """Llama al juez (segunda instancia de Claude)."""
    from claude_client import DEFAULT_MODEL, get_client, model_id

    try:
        client = get_client()
        r = client.messages.create(
            model=model_id(DEFAULT_MODEL), max_tokens=300, system=JUEZ_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": JUEZ_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"<pregunta>{pregunta}</pregunta>\n"
                f"<respuesta>{respuesta}</respuesta>\n"
                f"<rubrica>{rubrica}</rubrica>")}],
        )
        v = json.loads(r.content[0].text)
        return bool(v["cumple"]), v["razon"]
    except Exception as e:
        return False, f"Error en juez: {e}"


async def ejecutar_caso(pregunta: str, con_guardrails: bool) -> dict:
    """Ejecuta un caso a través del adaptador."""
    from adaptador import ejecutar

    resultado = await ejecutar(pregunta, con_guardrails=con_guardrails)
    return resultado


def correr(casos: list[dict], con_guardrails: bool) -> dict:
    """Corre todos los casos y retorna resultados."""
    print(f"\nGolden set: {len(casos)} casos · guardrails: {'SÍ' if con_guardrails else 'NO'}\n")

    filas = []
    for c in casos:
        caso_id = c["id"]
        pregunta = c["pregunta"]

        # Ejecuta caso
        resultado = asyncio.run(ejecutar_caso(pregunta, con_guardrails))

        # Califica por código
        checks = calificar_codigo(c.get("espera", {}), resultado)
        pasa_codigo = all(check[1] for check in checks)

        # Califica por juez si hay rúbrica
        pasa_juez = True
        juez_result = ""
        if c.get("juez"):
            pasa_juez, juez_result = juez(pregunta, resultado.get("respuesta", ""), c["juez"])

        # Veredicto final
        pasa = pasa_codigo and pasa_juez

        fila = {
            "caso": caso_id,
            "categoria": c.get("categoria", ""),
            "pasa_codigo": pasa_codigo,
            "pasa_juez": pasa_juez,
            "pasa": pasa,
            "checks": [{"nombre": ch[0], "ok": ch[1], "detalle": ch[2]} for ch in checks],
            "juez": juez_result,
            "respuesta": resultado.get("respuesta", "")[:200],  # primeros 200 chars
            "costo_haiku": resultado.get("costo_haiku_usd", 0),
        }
        filas.append(fila)

        # Imprime progreso
        estado = "✅" if pasa else "❌"
        print(f"{estado} {caso_id:3} {c.get('categoria', '')[:40]:40} {' / '.join(ch[0] for ch in checks if not ch[1])}")

    # Resumen
    pasan = sum(1 for f in filas if f["pasa"])
    print(f"\n{'='*60}")
    print(f"RESULTADO: {pasan}/{len(casos)} casos pasaron")
    print(f"Costo total: ${sum(f['costo_haiku'] for f in filas):.6f}")
    print(f"{'='*60}\n")

    return {
        "resumen": {"total": len(casos), "pasan": pasan, "pasan_pct": round(100 * pasan / len(casos))},
        "filas": filas,
    }


def comparar(antes_json: Path, despues_json: Path) -> None:
    """Compara dos ejecuciones."""
    antes = json.loads(antes_json.read_text())["filas"]
    despues = json.loads(despues_json.read_text())["filas"]

    print(f"\n{'='*60}")
    print("COMPARACIÓN")
    print(f"{'='*60}\n")

    mejoras = []
    regresiones = []
    for a, d in zip(antes, despues):
        if a["pasa"] and not d["pasa"]:
            regresiones.append(a["caso"])
        elif not a["pasa"] and d["pasa"]:
            mejoras.append(a["caso"])

    if mejoras:
        print(f"✅ MEJORAS: {', '.join(mejoras)}")
    if regresiones:
        print(f"❌ REGRESIONES: {', '.join(regresiones)}")
    if not mejoras and not regresiones:
        print("⏸️  Sin cambios")

    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-guardrails", action="store_true")
    parser.add_argument("--casos", help="casos a correr (p. ej. g01,g02)")
    parser.add_argument("--etiqueta", help="guarda resultados/<etiqueta>.json")
    parser.add_argument("--comparar", nargs=2, help="compara <antes>.json <despues>.json")
    a = parser.parse_args()

    if a.comparar:
        comparar(DIR_RESULTADOS / f"{a.comparar[0]}.json", DIR_RESULTADOS / f"{a.comparar[1]}.json")
        return

    casos = cargar_golden()
    if a.casos:
        ids = set(a.casos.split(","))
        casos = [c for c in casos if c["id"] in ids]

    resultados = correr(casos, con_guardrails=not a.sin_guardrails)

    if a.etiqueta:
        DIR_RESULTADOS.mkdir(exist_ok=True)
        ruta = DIR_RESULTADOS / f"{a.etiqueta}.json"
        ruta.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
        print(f"📁 Guardado en {ruta}")


if __name__ == "__main__":
    sys.exit(main())
