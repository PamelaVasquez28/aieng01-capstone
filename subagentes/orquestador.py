"""
L6 · Pasos 3 y 4: el orquestador, a mano con la Messages API (orchestrator-workers).

El orquestador NO tiene herramientas de datos ni de políticas: solo `delegar`. Planea, reparte tareas
acotadas a los subagentes (en el mismo turno si son independientes), recibe sus informes y escribe el
dictamen. Así su contexto queda limpio: ve informes, no las búsquedas crudas.

Ejecuta:
    python orquestador.py                 # el reclamo de laura.gomez
    python orquestador.py "otro reclamo"
"""

from __future__ import annotations

import json
import sys
import time

from claude_client import DEFAULT_MODEL, get_client, model_id
from paralelo import en_paralelo
from subagentes import SUBAGENTES, correr_subagente

DELEGAR = {
    "name": "delegar",
    "description": (
        "Encarga una tarea acotada a un subagente especializado y devuelve su informe. Subagentes: "
        + "; ".join(f"{n}: {c['descripcion']}" for n, c in SUBAGENTES.items())
        + ". La tarea debe ser autocontenida: el subagente NO ve esta conversación (incluye el cliente, qué buscar y "
        "para qué). Si dos tareas son independientes, delega las dos EN EL MISMO TURNO para que corran en paralelo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "subagente": {"type": "string", "enum": list(SUBAGENTES)},
            "tarea": {"type": "string", "description": "Instrucción autocontenida para el subagente"},
        },
        "required": ["subagente", "tarea"],
    },
}

SYSTEM = (
    "Eres el orquestador de reclamos complejos de PagosYa. No tienes acceso directo a datos ni a políticas: "
    "delega con la herramienta delegar. Planea primero qué necesitas saber, delega las tareas independientes en el "
    "mismo turno, y con los informes escribe un DICTAMEN para el agente humano con tres secciones: «Qué pasó» "
    "(hechos con IDs), «Qué dice la política» (con fuentes) y «Acciones recomendadas» (numeradas). Responde en español."
)

RECLAMO = (
    "Revisa el reclamo de laura.gomez: dice que le cobraron dos veces el plan Pro este mes, que la transferencia "
    "del arriendo lleva dos días retenida y que si no se resuelve hoy cancela el plan. Prepara el dictamen."
)


def orquestar(reclamo: str, max_vueltas: int = 5) -> str:
    client = get_client().with_options(max_retries=4, timeout=60)
    mensajes = [{"role": "user", "content": reclamo}]
    tokens = {"orquestador": 0}
    for vuelta in range(1, max_vueltas + 1):
        r = client.messages.create(model=model_id(DEFAULT_MODEL), max_tokens=1500, system=SYSTEM,
                                   tools=[DELEGAR], messages=mensajes)
        tokens["orquestador"] += r.usage.input_tokens + r.usage.output_tokens
        if r.stop_reason != "tool_use":
            print(f"\n[tokens] " + " · ".join(f"{k}={v}" for k, v in tokens.items()))
            return "".join(b.text for b in r.content if b.type == "text")
        mensajes.append({"role": "assistant", "content": r.content})
        llamadas = [b for b in r.content if b.type == "tool_use"]
        print(f"[orquestador] vuelta {vuelta}: delega {len(llamadas)} tarea(s) → "
              + ", ".join(b.input.get("subagente", "?") for b in llamadas), flush=True)
        t0 = time.time()
        salidas = en_paralelo([lambda b=b: correr_subagente(b.input["subagente"], b.input["tarea"]) for b in llamadas])
        print(f"[orquestador] informes recibidos en {time.time() - t0:.1f}s", flush=True)
        resultados = []
        for b, s in zip(llamadas, salidas):
            if s["ok"]:
                v = s["valor"]
                tokens[v["subagente"]] = tokens.get(v["subagente"], 0) + v["tokens"]
                resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": v["informe"]})
            else:
                resultados.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                   "content": f"El subagente falló ({s['error']}). Decide si reintentas con otra tarea o sigues sin ese dato."})
        mensajes.append({"role": "user", "content": resultados})
    return "[freno] el orquestador no terminó a tiempo"


if __name__ == "__main__":
    reclamo = " ".join(sys.argv[1:]) or RECLAMO
    print("=" * 70 + f"\nReclamo: {reclamo}\n" + "=" * 70)
    print("\nDICTAMEN:\n" + orquestar(reclamo))
