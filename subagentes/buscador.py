"""
L5 · El buscador: RAG ligero, sin base vectorial.

Trocea las políticas de `politicas/*.md` por sección (`## ...`) y las ordena con BM25, el ranking léxico
clásico de los buscadores. Sin embeddings ni servicios: corre en milisegundos y es fácil de depurar.
Lo importante de la sesión no es el algoritmo de ranking, es la forma: **la recuperación es una herramienta
que el agente decide usar**, y devuelve fragmentos cortos con su fuente, no documentos enteros.

Pruébalo solo:  python buscador.py "me cobraron dos veces"
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CARPETA = Path(__file__).parent / "politicas"

STOPWORDS = set("""a al algo como con cual cuando de del desde donde e el ella en entre es esta este esto la las le
lo los mas me mi mis muy no o para pero por que se si sin sobre su sus te tu un una uno unos y ya yo ha hay
hace dos mismo cada cuanto puedo quiero tengo""".split())


@dataclass
class Fragmento:
    fuente: str      # p. ej. "reembolsos.md#Cobros duplicados"
    texto: str
    tokens: list[str]


def normalizar(texto: str) -> list[str]:
    """minúsculas, sin tildes, sin signos, sin stopwords y sin la «s» del plural: «devolución» = «devolucion»."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    tokens = [t for t in re.findall(r"[a-z0-9]+", sin_tildes) if t not in STOPWORDS and len(t) > 1]
    return [t[:-1] if len(t) > 4 and t.endswith("s") else t for t in tokens]  # plural simple: «codigos» = «codigo»


def trocear(carpeta: Path = CARPETA) -> list[Fragmento]:
    """Un fragmento por sección `## `; el título del documento y de la sección van dentro del texto."""
    fragmentos = []
    for archivo in sorted(carpeta.glob("*.md")):
        titulo_doc, seccion, lineas = "", None, []

        def cerrar():
            if seccion and lineas:
                texto = f"{titulo_doc} · {seccion}\n" + " ".join(l.strip() for l in lineas if l.strip())
                fragmentos.append(Fragmento(f"{archivo.name}#{seccion}", texto, normalizar(texto)))

        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.startswith("# "):
                titulo_doc = linea[2:].strip()
            elif linea.startswith("## "):
                cerrar()
                seccion, lineas = linea[3:].strip(), []
            else:
                lineas.append(linea)
        cerrar()
    return fragmentos


class Buscador:
    def __init__(self, fragmentos: list[Fragmento] | None = None, k1: float = 1.5, b: float = 0.75):
        self.frag = fragmentos if fragmentos is not None else trocear()
        self.k1, self.b = k1, b
        self.largo_medio = sum(len(f.tokens) for f in self.frag) / max(len(self.frag), 1)
        df = Counter(t for f in self.frag for t in set(f.tokens))
        n = len(self.frag)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def puntaje(self, consulta: list[str], f: Fragmento) -> float:
        tf = Counter(f.tokens)
        s = 0.0
        for t in consulta:
            if t in tf:
                num = tf[t] * (self.k1 + 1)
                den = tf[t] + self.k1 * (1 - self.b + self.b * len(f.tokens) / self.largo_medio)
                s += self.idf.get(t, 0) * num / den
        return s

    def buscar(self, consulta: str, k: int = 3) -> list[tuple[float, Fragmento]]:
        q = normalizar(consulta)
        ranking = sorted(((self.puntaje(q, f), f) for f in self.frag), key=lambda x: -x[0])
        return [(s, f) for s, f in ranking[:k] if s > 0]


if __name__ == "__main__":
    b = Buscador()
    consulta = " ".join(sys.argv[1:]) or "me cobraron dos veces el plan"
    print(f"{len(b.frag)} fragmentos indexados · consulta: «{consulta}»\n")
    for s, f in b.buscar(consulta):
        print(f"[{s:5.2f}] {f.fuente}\n        {f.texto[:140]}…\n")
