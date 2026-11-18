"""
L4 · Revisor de Declaraciones de Origen (DO) con Claude Agent SDK + MCP.

Ejecuta:
    python agente.py "Revisa el DO 26-0001 y dime si está listo para declarar"
"""

import os
import sys
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultError,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from politica import hook_politica
from sdk_config import MODELO, proveedor

from claude_agent_sdk import AgentDefinition

AQUI = Path(__file__).parent

SYSTEM = (
    "Revisor de Declaraciones de Origen. "
    "1. buscar_do(numero). Si no existe → 'El DO XX-XXXX no existe'. Si fuera de alcance → 'No puedo, eso está fuera de mi alcance'.\n"
    "2. requisitos_modalidad(modalidad). ¿Todos documentos requeridos 'cargado' Y valor_factura == valor_dav?\n"
    "3. Si LISTO → SALIDA FINAL directa.\n"
    "4. Si INCOMPLETO → llama verificador UNA sola vez con dictamen. Si ERROR, corrige.\n"
    "5. SALIDA:\n"
    "DICTAMEN: LISTO\n"
    "O DICTAMEN: INCOMPLETO\n"
    "- documento: razón"
)

SERVIDORES = {
    "aduana": {"type": "stdio", "command": sys.executable, "args": [str(AQUI / "server.py")]},
}

# Herramientas del MCP de aduanas
HERRAMIENTAS = [
    "mcp__aduana__buscar_do",
    "mcp__aduana__listar_documentos",
    "mcp__aduana__requisitos_modalidad",
]

# Subagente verificador (solo contrasta documentos, no busca el DO)
AGENTES = {
    "verificador": AgentDefinition(
        description="Verifica que el dictamen del revisor sea correcto contrastándolo contra los documentos reales.",
        prompt=(
            "Tu tarea: valida un DICTAMEN de DO contrastándolo contra los documentos reales.\n"
            "Recibe el DICTAMEN (LISTO o INCOMPLETO con lista de problemas).\n"
            "Consulta requisitos_modalidad(modalidad) y listar_documentos(numero).\n"
            "Verifica que el DICTAMEN sea EXACTO: que los problemas listados sean reales y que no falten problemas.\n"
            "Respuesta: 'OK: <motivo breve>' o 'ERROR: <qué no cuadra>'."
        ),
        tools=[
            "mcp__aduana__listar_documentos",
            "mcp__aduana__requisitos_modalidad",
        ],
        model="inherit",
    )
}


def opciones(**extra) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODELO,
        system_prompt=SYSTEM,
        mcp_servers=SERVIDORES,
        agents=AGENTES,
        tools=["Agent"],
        allowed_tools=["Agent"] + HERRAMIENTAS,
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook_politica])]},
        setting_sources=[],
        max_turns=int(os.environ.get("MAX_TURNOS", "8")),  # Reducido: 15→8
        max_budget_usd=float(os.environ.get("PRESUPUESTO_USD", "0.50")),
        cwd=str(AQUI),
        **extra,
    )


def mostrar(m) -> None:
    """Traza: herramientas, respuesta, turnos y costo."""
    if isinstance(m, AssistantMessage):
        for b in m.content:
            if isinstance(b, ToolUseBlock):
                print(f"  [tool] {b.name}({b.input})", flush=True)
            elif isinstance(b, TextBlock) and b.text.strip():
                print(f"\nRevisor: {b.text.strip()}", flush=True)
    elif isinstance(m, UserMessage) and isinstance(m.content, list):
        for b in m.content:
            if isinstance(b, ToolResultBlock):
                print(f"    → {'error' if b.is_error else 'ok'}", flush=True)
    elif isinstance(m, ResultMessage):
        costo = f"USD {m.total_cost_usd:.4f}" if m.total_cost_usd is not None else "s/d"
        print(f"\n[resultado] {m.subtype} · turnos={m.num_turns} · costo≈{costo} · {m.duration_ms / 1000:.1f}s", flush=True)


async def correr(mision: str) -> ResultMessage:
    """Ejecuta la misión y retorna el ResultMessage final."""
    resultado = None
    try:
        async for m in query(prompt=mision, options=opciones()):
            mostrar(m)
            if isinstance(m, ResultMessage):
                resultado = m
    except ResultError as exc:
        print(f"[freno] {exc}", flush=True)
    return resultado


async def correr_json(mision: str) -> dict:
    """Ejecuta la misión y retorna resultado en JSON para ser consumido por adaptador.py."""
    import json as json_lib
    respuesta_texto = ""
    tokens_entrada = 0
    tokens_salida = 0
    costo = 0.0

    try:
        async for m in query(prompt=mision, options=opciones()):
            if isinstance(m, AssistantMessage):
                for b in m.content:
                    if isinstance(b, TextBlock) and b.text.strip():
                        respuesta_texto += "\n" + b.text
            elif isinstance(m, ResultMessage):
                # ResultMessage tiene: total_cost_usd, num_turns, duration_ms, subtype
                # Los tokens no están en ResultMessage; se pasan a través de usage que no está accesible aquí
                # Aproximación: guardarlos si lo necesitamos después
                costo = m.total_cost_usd or 0.0
    except ResultError:
        pass

    # Aproximación: extraer tokens de la respuesta si es necesario, o dejar en 0
    # En realidad, los tokens están en los mensajes intermedios pero no en ResultMessage
    return {
        "respuesta": respuesta_texto.strip(),
        "tokens_entrada": 0,  # No disponible en ResultMessage
        "tokens_salida": 0,   # No disponible en ResultMessage
        "costo_usd": costo,
    }


if __name__ == "__main__":
    mision = " ".join(sys.argv[1:]) or "Revisa el DO 26-0001 y dime si está listo para declarar"
    modo = sys.argv[-1] if sys.argv[-1] in ("--json",) else None

    if modo == "--json":
        # Modo JSON para adaptador.py
        import json as json_lib
        resultado = anyio.run(correr_json, mision)
        print(json_lib.dumps(resultado, ensure_ascii=False))
    else:
        # Modo normal con traza visible
        print("=" * 70)
        print(f"  Misión: {mision}")
        print(f"  {proveedor()} · {MODELO}")
        print("=" * 70)
        anyio.run(correr, mision)
