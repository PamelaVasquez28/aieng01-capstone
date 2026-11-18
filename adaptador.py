"""
Adaptador: ejecuta el revisor de DO con guardrails, registra traza y costo.

Interfaz compatible con evals.py.

Ejecuta:
    python adaptador.py "Revisa el DO 26-0002 y dime si está listo para declarar"
    python adaptador.py "Revisa el DO 26-0002 y dime si está listo para declarar" --sin-guardrails
"""

import sys
import asyncio
from pathlib import Path

from guardrails import guardrail_entrada, guardrail_salida
from costing import log_usage, cost_usd
from trazas import Traza
from sdk_config import MODELO

from claude_agent_sdk import (
    query,
    ResultMessage,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultError,
)
from agente import opciones

AQUI = Path(__file__).parent


async def ejecutar_agente_sdk(pregunta: str) -> tuple[str, list[str], int, int, int, int, float, float]:
    """
    Ejecuta agente contra MCP, retorna:
    (respuesta_texto, herramientas_usadas, tokens_entrada, tokens_salida, cache_write, cache_read, costo_sdk_usd, costo_haiku_usd)
    """
    respuesta_texto = ""
    herramientas_usadas = []
    tokens_entrada = 0
    tokens_salida = 0
    cache_write = 0
    cache_read = 0
    costo_sdk = 0.0
    costo_haiku = 0.0

    try:
        async for m in query(prompt=pregunta, options=opciones()):
            if isinstance(m, AssistantMessage):
                for b in m.content:
                    if isinstance(b, ToolUseBlock):
                        if b.name not in herramientas_usadas:
                            herramientas_usadas.append(b.name)
                    elif isinstance(b, TextBlock) and b.text.strip():
                        respuesta_texto = b.text

            elif isinstance(m, ResultMessage):
                costo_sdk = m.total_cost_usd or 0.0

                # Extrae tokens del usage dict
                if hasattr(m, "usage") and m.usage and isinstance(m.usage, dict):
                    tokens_entrada = m.usage.get("input_tokens", 0) or 0
                    tokens_salida = m.usage.get("output_tokens", 0) or 0
                    cache_write = m.usage.get("cache_creation_input_tokens", 0) or 0
                    cache_read = m.usage.get("cache_read_input_tokens", 0) or 0

    except ResultError:
        pass

    # Calcula costo Haiku con los tokens reales
    if tokens_entrada > 0 or tokens_salida > 0:
        class UsageStub:
            def __init__(self, inp, out, cw, cr):
                self.input_tokens = inp
                self.output_tokens = out
                self.cache_creation_input_tokens = cw
                self.cache_read_input_tokens = cr

        uso = UsageStub(tokens_entrada, tokens_salida, cache_write, cache_read)
        costo_haiku = cost_usd(uso, MODELO)
    else:
        costo_haiku = 0.0

    return respuesta_texto.strip(), herramientas_usadas, tokens_entrada, tokens_salida, cache_write, cache_read, costo_sdk, costo_haiku


async def ejecutar(pregunta: str, con_guardrails: bool = True) -> dict:
    """Ejecuta el revisor; retorna respuesta, herramientas, modelo, tokens, costos."""

    # Guardrails de entrada
    if con_guardrails:
        razon_rechazo = guardrail_entrada(pregunta)
        if razon_rechazo:
            return {
                "respuesta": f"❌ Solicitud rechazada: {razon_rechazo}",
                "herramientas_usadas": [],
                "modelo": MODELO,
                "tokens_entrada": 0,
                "tokens_salida": 0,
                "costo_sdk_usd": 0,
                "costo_haiku_usd": 0,
                "rechazado": True,
            }

    # Ejecuta agente
    respuesta_texto, herramientas_usadas, tokens_entrada, tokens_salida, cache_write, cache_read, costo_sdk, costo_haiku = await ejecutar_agente_sdk(pregunta)

    if not respuesta_texto:
        return {
            "respuesta": "❌ Error: el agente no retornó una respuesta.",
            "herramientas_usadas": [],
            "modelo": MODELO,
            "tokens_entrada": 0,
            "tokens_salida": 0,
            "costo_sdk_usd": 0,
            "costo_haiku_usd": 0,
            "error": True,
        }

    # Guardrails de salida
    if con_guardrails:
        respuesta_texto = guardrail_salida(respuesta_texto)

    # Registra uso en usage_log.jsonl
    class UsageStub:
        def __init__(self, input_tokens, output_tokens):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens

    uso_stub = UsageStub(tokens_entrada, tokens_salida)
    log_usage("adaptador_aduana", MODELO, uso_stub)

    return {
        "respuesta": respuesta_texto,
        "herramientas_usadas": herramientas_usadas,
        "modelo": MODELO,
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "costo_sdk_usd": costo_sdk,
        "costo_haiku_usd": costo_haiku,
    }


async def main():
    if len(sys.argv) < 2:
        print("Uso: python adaptador.py <pregunta> [--sin-guardrails]")
        sys.exit(1)

    pregunta = sys.argv[1]
    sin_guardrails = "--sin-guardrails" in sys.argv

    print(f"🔍 Ejecutando: {pregunta}")
    print(f"   Guardrails: {'❌ desactivados' if sin_guardrails else '✅ activados'}\n")

    resultado = await ejecutar(pregunta, con_guardrails=not sin_guardrails)

    # Imprime resultado
    print(f"📋 RESPUESTA:\n{resultado['respuesta']}\n")
    print(f"🔧 Herramientas: {', '.join(resultado['herramientas_usadas']) if resultado['herramientas_usadas'] else 'ninguna'}")
    print(f"🤖 Modelo: {resultado['modelo']}")
    print(f"📊 Tokens: {resultado['tokens_entrada']} entrada, {resultado['tokens_salida']} salida")
    print(f"💰 Costo SDK: ${resultado['costo_sdk_usd']:.6f}")
    print(f"💰 Costo Haiku: ${resultado['costo_haiku_usd']:.6f}")

    # Guarda traza
    traza = Traza(pregunta)
    traza.evento("adaptador", "entrada", pregunta=pregunta, sin_guardrails=sin_guardrails)
    traza.evento("adaptador", "salida", **resultado)
    ruta = traza.cerrar()
    print(f"📝 Traza guardada en {ruta}")


if __name__ == "__main__":
    asyncio.run(main())
