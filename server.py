"""
MCP "aduana": Servidor para consultar Declaraciones de Origen (DO).

Ejecuta standalone:   python server.py
Inspecciona (opt):    npx @modelcontextprotocol/inspector python server.py

Herramientas:
  - buscar_do(numero): Busca un DO por número; devuelve sus datos.
  - listar_documentos(numero): Lista los documentos del DO.
  - requisitos_modalidad(modalidad): Devuelve los requisitos para consumo o temporal.
"""

import json
import os
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

mcp = FastMCP("aduana", log_level="WARNING")

AQUI = Path(__file__).parent
DOS_DB = AQUI / "datos" / "dos.json"
REQUISITOS_DB = AQUI / "datos" / "requisitos.json"


def _load_dos() -> dict:
    return json.loads(DOS_DB.read_text(encoding="utf-8"))


def _load_requisitos() -> dict:
    return json.loads(REQUISITOS_DB.read_text(encoding="utf-8"))


@mcp.tool()
def buscar_do(numero: str) -> dict:
    """Busca una Declaración de Origen (DO) por su número (p. ej. 26-0001).
    Devuelve: numero, importador, modalidad, valor_factura_usd, valor_dav_usd, documentos.
    Levanta error si el DO no existe."""
    dos = _load_dos()
    if numero not in dos:
        raise ToolError(f"El DO {numero} no existe en el sistema. Verifica el número e intenta de nuevo.")
    return dos[numero]


@mcp.tool()
def listar_documentos(numero: str) -> list[dict]:
    """Lista todos los documentos asociados al DO con su tipo, número y estado.
    Estados posibles: cargado, pendiente, vencido.
    Levanta error si el DO no existe."""
    dos = _load_dos()
    if numero not in dos:
        raise ToolError(f"El DO {numero} no existe. No se pueden listar documentos.")
    return dos[numero]["documentos"]


@mcp.tool()
def requisitos_modalidad(modalidad: Literal["consumo", "temporal"]) -> list[str]:
    """Devuelve la lista de tipos de documentos requeridos para una modalidad.
    Modalidades válidas: consumo, temporal."""
    requisitos = _load_requisitos()
    if modalidad not in requisitos:
        raise ToolError(f"Modalidad '{modalidad}' no reconocida. Válidas: consumo, temporal.")
    return requisitos[modalidad]


if __name__ == "__main__":
    mcp.run()
