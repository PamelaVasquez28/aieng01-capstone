"""
L6 · Las herramientas de los subagentes, como funciones puras (las usan el orquestador manual y el del SDK).

Cada subagente recibe SOLO las suyas: el investigador lee datos del cliente, el experto lee políticas.
Ninguno puede escribir. Separar permisos por subagente es una de las razones para tener subagentes.
"""

from __future__ import annotations

import json
from pathlib import Path

from buscador import Buscador

DATOS = json.loads((Path(__file__).parent / "datos.json").read_text(encoding="utf-8"))
_BUSCADOR = Buscador()


def consultar_movimientos(cliente: str) -> dict:
    if cliente not in DATOS["movimientos"]:
        raise LookupError(f"No hay cliente «{cliente}». Usa el username exacto (p. ej. laura.gomez).")
    return {"cliente": cliente, "movimientos": DATOS["movimientos"][cliente]}


def consultar_casos(cliente: str) -> dict:
    return {"cliente": cliente, "casos": DATOS["casos"].get(cliente, [])}


def buscar_politicas(consulta: str, k: int = 3) -> dict:
    r = _BUSCADOR.buscar(consulta, k=k)
    if not r:
        return {"fragmentos": [], "nota": "Sin resultados: reformula con otras palabras clave."}
    return {"fragmentos": [{"fuente": f.fuente, "texto": f.texto} for _, f in r]}


IMPLS = {"consultar_movimientos": consultar_movimientos, "consultar_casos": consultar_casos,
         "buscar_politicas": buscar_politicas}

SCHEMAS = {
    "consultar_movimientos": {
        "name": "consultar_movimientos",
        "description": "Cargos y transferencias de un cliente (username, p. ej. laura.gomez), con fecha, monto y estado.",
        "input_schema": {"type": "object", "properties": {"cliente": {"type": "string"}}, "required": ["cliente"]},
    },
    "consultar_casos": {
        "name": "consultar_casos",
        "description": "Casos de soporte de un cliente (username), con estado, prioridad y fecha de apertura.",
        "input_schema": {"type": "object", "properties": {"cliente": {"type": "string"}}, "required": ["cliente"]},
    },
    "buscar_politicas": {
        "name": "buscar_politicas",
        "description": ("Busca en las políticas oficiales de PagosYa y devuelve fragmentos con su fuente. La búsqueda "
                        "es por palabras: si no encuentras, reformula (p. ej. «cobro duplicado»)."),
        "input_schema": {"type": "object", "properties": {"consulta": {"type": "string"}, "k": {"type": "integer"}},
                         "required": ["consulta"]},
    },
}


def ejecutar(nombre: str, entrada: dict) -> dict:
    try:
        return {"content": json.dumps(IMPLS[nombre](**entrada), ensure_ascii=False)}
    except (LookupError, TypeError, ValueError) as exc:
        return {"is_error": True, "content": f"{exc}"}
