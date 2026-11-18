"""
L6 · Paso 4: lanzar subagentes en paralelo, lo implementas tú.

Cuando el orquestador delega dos tareas independientes en el mismo turno, correrlas una tras otra suma sus
latencias. En paralelo, el turno dura lo que dura la más lenta. Y si una falla, la otra no debe perderse:
el orquestador recibe la falla como dato y decide.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor  # noqa: F401  (lo vas a usar)
from typing import Any


def en_paralelo(tareas: list[Callable[[], Any]], max_concurrencia: int = 4) -> list[dict]:
    """Ejecuta cada tarea (una función sin argumentos) y devuelve un resultado por tarea, EN EL MISMO ORDEN.

    Cada resultado es {"ok": True, "valor": <lo que devolvió>} o, si lanzó una excepción,
    {"ok": False, "error": "<TipoDeExcepción>: <mensaje>"}.

    Reglas (TODO paso 4):
      1. Las tareas corren a la vez, con a lo sumo `max_concurrencia` al mismo tiempo (ThreadPoolExecutor).
      2. El orden de los resultados es el de `tareas`, no el orden en que terminan.
      3. Una excepción en una tarea NO interrumpe las demás: se vuelve {"ok": False, ...}.
    """
    return [{"ok": True, "valor": t()} for t in tareas]  # TODO paso 4: hoy es secuencial y una falla lo rompe todo
