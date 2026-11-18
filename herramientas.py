"""
L7 (♻ L2) · Las tres herramientas del agente de soporte de PagosYa (sistemas internos simulados).

Cada herramienta falla de UNA manera distinta, a propósito, porque en producción tu loop
tiene que tratar distinto cada clase de error:

| Excepción          | Ejemplo                                   | Qué hace el loop                         |
|--------------------|-------------------------------------------|------------------------------------------|
| ErrorDeEntrada     | documento con puntos: "1.020.304.050"     | NO reintenta: le devuelve al modelo un   |
|                    |                                           | error accionable para que corrija        |
| NoEncontrado       | cliente o transferencia que no existe     | NO reintenta: el dato no va a aparecer   |
| ErrorTransitorio   | el core bancario no responde (timeout)    | SÍ reintenta, con backoff (reintentos.py)|

El core bancario falla las primeras N llamadas, con N = variable de entorno FALLAS_CORE
(0 por defecto). Así puedes reproducir una caída sin depender de la suerte.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

_DATOS = json.loads((Path(__file__).parent / "datos.json").read_text(encoding="utf-8"))


class ErrorDeEntrada(Exception):
    """Los argumentos no cumplen el contrato de la herramienta. Reintentar igual no sirve."""


class NoEncontrado(Exception):
    """El recurso no existe. Reintentar no lo va a hacer aparecer."""


class ErrorTransitorio(Exception):
    """El sistema de abajo falló de forma temporal (timeout, 503). Reintentar sí puede funcionar."""


# ── Core bancario con fallas controladas ─────────────────────────────────────────────────────
_fallas_restantes = int(os.environ.get("FALLAS_CORE", "0"))


def configurar_fallas(n: int) -> None:
    """Hace que las próximas `n` llamadas al core bancario fallen (para pruebas)."""
    global _fallas_restantes
    _fallas_restantes = n


def _core_bancario() -> None:
    global _fallas_restantes
    if _fallas_restantes > 0:
        _fallas_restantes -= 1
        raise ErrorTransitorio("el core bancario no respondió (timeout de 3 s)")


# ── Herramienta 1 ────────────────────────────────────────────────────────────────────────────
def buscar_cliente(documento: str) -> dict:
    if not re.fullmatch(r"\d{6,10}", documento or ""):
        raise ErrorDeEntrada(
            f"documento '{documento}' inválido: debe ir solo con dígitos (6 a 10), sin puntos, "
            "espacios ni prefijos como 'CC'. Ejemplo: 1020304050"
        )
    cliente = _DATOS["clientes"].get(documento)
    if cliente is None:
        raise NoEncontrado(f"no hay ningún cliente con documento {documento}")
    return cliente


# ── Herramienta 2 ────────────────────────────────────────────────────────────────────────────
ESTADOS = ["completada", "retenida", "rechazada", "en_proceso"]


def consultar_transferencias(cliente_id: str, estado: str | None = None) -> dict:
    if estado is not None and estado not in ESTADOS:
        raise ErrorDeEntrada(f"estado '{estado}' inválido; usa uno de {ESTADOS} u omítelo")
    if cliente_id not in _DATOS["transferencias"]:
        raise NoEncontrado(f"no hay transferencias para el cliente {cliente_id}; ¿usaste el cliente_id que devolvió buscar_cliente?")
    _core_bancario()  # ← aquí puede saltar un ErrorTransitorio
    filas = [t for t in _DATOS["transferencias"][cliente_id] if estado is None or t["estado"] == estado]
    return {"cliente_id": cliente_id, "transferencias": filas}


# ── Herramienta 3 (idempotente) ──────────────────────────────────────────────────────────────
_casos: dict[tuple, str] = {}


def crear_caso(cliente_id: str, resumen: str, prioridad: str, transferencia_id: str | None = None) -> dict:
    if prioridad not in ("alta", "media", "baja"):
        raise ErrorDeEntrada("prioridad debe ser 'alta', 'media' o 'baja'")
    if len(resumen.strip()) < 10:
        raise ErrorDeEntrada("el resumen es demasiado corto: describe el problema en una frase completa")
    # Idempotencia: el mismo problema del mismo cliente no abre dos casos, aunque el loop
    # (o un reintento) llame dos veces. La clave es lo que identifica el problema, no el texto.
    clave = (cliente_id, transferencia_id or resumen.strip().lower())
    if clave in _casos:
        return {"caso_id": _casos[clave], "nuevo": False, "prioridad": prioridad}
    caso_id = f"CASO-{len(_casos) + 1001}"
    _casos[clave] = caso_id
    return {"caso_id": caso_id, "nuevo": True, "prioridad": prioridad}


def reiniciar_estado() -> None:
    """Vuelve al estado inicial (sin casos abiertos, core sano). Lo usa evals.py antes de cada caso del golden set:
    un eval que depende del caso anterior no mide nada."""
    _casos.clear()
    configurar_fallas(0)


TOOL_IMPLS = {
    "buscar_cliente": buscar_cliente,
    "consultar_transferencias": consultar_transferencias,
    "crear_caso": crear_caso,
}

# Lo que el MODELO ve. La description es la mitad de la calidad de una herramienta: di cuándo
# usarla, qué devuelve y qué hacer con sus errores.
TOOLS = [
    {
        "name": "buscar_cliente",
        "description": (
            "Busca un cliente de PagosYa por su número de documento y devuelve su cliente_id. "
            "Úsala SIEMPRE primero: las otras herramientas necesitan el cliente_id, no el documento. "
            "El documento va solo con dígitos (quita puntos, espacios y prefijos como 'CC')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"documento": {"type": "string", "description": "Solo dígitos, ej: 1020304050"}},
            "required": ["documento"],
        },
    },
    {
        "name": "consultar_transferencias",
        "description": (
            "Lista las transferencias recientes de un cliente, con estado y motivo. "
            "Úsala cuando el usuario pregunte por una transferencia, un pago o un dinero que no llegó. "
            "Si devuelve un error del core bancario, NO la vuelvas a llamar en este turno."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "El cliente_id de buscar_cliente, ej: C-001"},
                "estado": {"type": "string", "enum": ESTADOS, "description": "Filtro opcional"},
            },
            "required": ["cliente_id"],
        },
    },
    {
        "name": "crear_caso",
        "description": (
            "Abre un caso de soporte para que lo atienda una persona. Úsala solo si el usuario lo pide "
            "o si el problema no se resuelve con información (p. ej. una transferencia retenida que el "
            "usuario necesita liberar). Es idempotente: llamarla dos veces por el mismo problema "
            "devuelve el mismo caso_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string"},
                "resumen": {"type": "string", "description": "El problema en una frase"},
                "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
                "transferencia_id": {"type": "string", "description": "Si el caso es por una transferencia, su id (T-...)"},
            },
            "required": ["cliente_id", "resumen", "prioridad"],
        },
    },
]
