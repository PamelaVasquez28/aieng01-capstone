"""
L6 · Verificación del lab, sin llamar al modelo (corre en segundos).

Ejecuta: python verificar.py
Antes del paso 4 vas a ver fallas en «paralelo»: es lo esperado. Al terminar el lab: 8/8.
"""

import sys
import threading
import time

resultados: list[bool] = []


def check(nombre, fn):
    try:
        fn()
        resultados.append(True)
        print(f"✅ {nombre}")
    except Exception as exc:  # noqa: BLE001
        resultados.append(False)
        print(f"❌ {nombre}: {type(exc).__name__}: {exc}")


def datos_duplicado():
    from herramientas import consultar_movimientos
    cargos = [m for m in consultar_movimientos("laura.gomez")["movimientos"] if m["tipo"] == "cargo"]
    assert len(cargos) == 2 and cargos[0]["fecha"] == cargos[1]["fecha"], "esperaba los 2 cargos del mismo día"


def politica_retenidas():
    from herramientas import buscar_politicas
    fuentes = [f["fuente"] for f in buscar_politicas("transferencia retenida liberar")["fragmentos"]]
    assert fuentes and fuentes[0] == "transferencias.md#Transferencias retenidas", fuentes


def delegar_conoce_subagentes():
    from orquestador import DELEGAR
    from subagentes import SUBAGENTES
    assert DELEGAR["input_schema"]["properties"]["subagente"]["enum"] == list(SUBAGENTES)


def permisos_separados():
    from subagentes import SUBAGENTES
    assert SUBAGENTES["experto_politicas"]["herramientas"] == ["buscar_politicas"], "el experto solo lee políticas"
    assert "buscar_politicas" not in SUBAGENTES["investigador_cuenta"]["herramientas"], "el investigador no lee políticas"


def paralelo_orden():
    from paralelo import en_paralelo
    r = en_paralelo([lambda i=i: i * 10 for i in range(5)])
    assert [x.get("valor") for x in r] == [0, 10, 20, 30, 40], r


def paralelo_aisla_fallas():
    from paralelo import en_paralelo

    def falla():
        raise LookupError("cliente inexistente")
    r = en_paralelo([lambda: "a", falla, lambda: "c"])
    assert r[0] == {"ok": True, "valor": "a"} and r[2] == {"ok": True, "valor": "c"}, r
    assert r[1]["ok"] is False and "LookupError" in r[1]["error"], r[1]


def paralelo_concurrente():
    from paralelo import en_paralelo
    t0 = time.time()
    en_paralelo([lambda: time.sleep(0.3) for _ in range(3)])
    dt = time.time() - t0
    assert dt < 0.6, f"3 tareas de 0,3 s tardaron {dt:.2f} s: no corrieron a la vez"


def paralelo_respeta_limite():
    from paralelo import en_paralelo
    activos, pico, lock = [0], [0], threading.Lock()

    def tarea():
        with lock:
            activos[0] += 1
            pico[0] = max(pico[0], activos[0])
        time.sleep(0.1)
        with lock:
            activos[0] -= 1
    en_paralelo([tarea] * 6, max_concurrencia=2)
    assert pico[0] == 2, f"con max_concurrencia=2 el pico fue {pico[0]}"


check("datos: los 2 cargos del plan Pro del mismo día", datos_duplicado)
check("políticas: «transferencia retenida» encuentra la sección correcta", politica_retenidas)
check("orquestador: delegar solo conoce a los subagentes definidos", delegar_conoce_subagentes)
check("subagentes: cada uno con SUS herramientas", permisos_separados)
check("paralelo: devuelve en el mismo orden", paralelo_orden)
check("paso 4 · paralelo: una falla no rompe las demás", paralelo_aisla_fallas)
check("paso 4 · paralelo: las tareas corren a la vez", paralelo_concurrente)
check("paso 4 · paralelo: respeta max_concurrencia", paralelo_respeta_limite)

print(f"\nVERIFICACIÓN L6: {sum(resultados)}/{len(resultados)}")
sys.exit(0 if all(resultados) else 1)
