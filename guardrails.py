"""
Guardrails de entrada y salida para el revisor de Declaraciones de Origen.

Entrada: detecta inyección de instrucciones y pedidos de datos sensibles.
Salida: exige LISTO/INCOMPLETO o una negativa válida (no existe, no puedo, fuera de alcance); enmascara NIT/teléfono/correo.
"""

import re

PATRONES_INYECCION = [
    r"ignora\w*\s+(todas?\s+)?(las\s+|tus\s+)?(instrucciones|reglas)",
    r"olvida\w*\s+(todas?\s+)?(las\s+|tus\s+)?(instrucciones|reglas)",
    r"(system|sistema)\s*prompt",
    r"(modo|mode)\s+(desarrollador|developer|dios|admin)",
    r"ahora\s+eres\s+",
    r"marca\w*\s+como\s+listo",
    r"fuerza.*listo",
]

PATRONES_PII_ENTRADA = [
    r"\bnit\b",
    r"\bteléfono\b",
    r"\btelefono\b",
    r"\bcorreo\b",
    r"\bemail\b",
]

PATRONES_SALIDA_VALIDA = [
    r"\blisto\b",
    r"\bincompleto\b",
    r"no existe",
    r"no encontr",
    r"no aparece",
    r"no figura",
    r"no puedo",
    r"no estoy",
    r"fuera de alcance",
    r"rechaz",
    r"niega",
]

PATRONES_PII_SALIDA = [
    r"\d{9,11}(?!\d)",  # NIT aproximado (9-11 dígitos, no seguidos de más dígitos)
    r"\+?57[\s\-.]?\d{2,4}[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}",  # Teléfono Colombia
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # Email
]


def guardrail_entrada(texto: str) -> str | None:
    """Detecta inyección o pedidos de PII. Retorna razón de rechazo o None si está bien."""
    texto_lower = texto.lower()

    # Inyección
    for patron in PATRONES_INYECCION:
        if re.search(patron, texto_lower, re.IGNORECASE):
            return "Detecté una tentativa de inyección de instrucciones. Por favor, haz una pregunta legítima sobre un DO."

    # PII sensible
    for patron in PATRONES_PII_ENTRADA:
        if re.search(patron, texto_lower, re.IGNORECASE):
            return "No puedo proporcionar datos sensibles del importador (NIT, teléfono, correo)."

    return None


def guardrail_salida(texto: str) -> str:
    """Valida que la respuesta sea segura: contiene veredicto válido y sin PII expuesta."""
    texto_lower = texto.lower()

    # Asegura que hay un veredicto válido (LISTO, INCOMPLETO, o negativa válida)
    tiene_veredicto = any(re.search(p, texto_lower, re.IGNORECASE) for p in PATRONES_SALIDA_VALIDA)
    if not tiene_veredicto:
        return "⚠️  Respuesta incompleta: debe contener un dictamen LISTO/INCOMPLETO, o indicar que no existe, está fuera de alcance, o no se puede procesar."

    # Enmascara PII en la respuesta
    resultado = texto
    for patron in PATRONES_PII_SALIDA:
        resultado = re.sub(patron, "[DATOS_SENSIBLES]", resultado, flags=re.IGNORECASE)

    return resultado
