# L6 · Orquestador con 2 subagentes especializados

> **AIENG01 · Sesión 6** · En clase: **60 min** (pasos 1 a 6) · Extensión opcional, en casa: el reto del
> paso 6.

## Contexto

Llega a PagosYa un reclamo que mezcla todo: un doble cobro, una transferencia retenida y una amenaza de
cancelar el plan. Un solo agente con todas las herramientas puede resolverlo, pero su contexto se llena de
movimientos crudos y fragmentos de políticas, y se le mezclan los roles. Hoy lo resuelves con el patrón
**orquestador-trabajadores**: un orquestador que planea y delega, y dos subagentes especializados, cada uno
con **su contexto limpio, sus herramientas y su formato de entrega**.

> Pregunta ancla: ¿cuándo vale la pena pagar varios agentes en lugar de uno?

## Objetivos de aprendizaje

- Diseñar subagentes con rol, herramientas propias (mínimo privilegio) y un formato de entrega.
- Construir el orquestador a mano: una herramienta `delegar`, tareas autocontenidas y síntesis.
- Lanzar subagentes en paralelo y aislar sus fallas (lo implementas tú).
- Hacer lo mismo con `agents=` del Claude Agent SDK y comparar.
- Medir el costo: tokens por agente.

## Estructura

```
workspace/
├── subagentes.py       # investigador_cuenta y experto_politicas: rol, herramientas, loop propio
├── herramientas.py     # consultar_movimientos, consultar_casos, buscar_politicas (solo lectura)
├── paralelo.py         # Paso 4: TU en_paralelo (TODO)
├── orquestador.py      # Pasos 3-4: el orquestador a mano (Messages API)
├── orquestador_sdk.py  # Paso 5: lo mismo con agents= del Agent SDK
├── verificar.py        # Verificación sin modelo (8/8 al terminar)
├── datos.json · politicas/ · buscador.py   # los datos de PagosYa y el buscador del L5
├── claude_client.py · sdk_config.py        # Bedrock en el workspace
└── requirements.txt
```

## Tiempos en clase

| Paso | Qué haces | Minutos |
|---|---|---|
| 1 | Entorno y verificación de partida | 5 |
| 2 | Un subagente, solo | 8 |
| 3 | El orquestador: delegar y sintetizar | 12 |
| 4 | Subagentes en paralelo: **lo implementas tú** | 15 |
| 5 | Lo mismo con el Agent SDK (`agents=`) | 12 |
| 6 | Costo, cuándo sí y cuándo no, y cierre | 8 |

## Conexión con el curso

Sesión 6 · Orquestación multi-agente. Tu proyecto integrador exige al menos un subagente. En la
**sesión 7** mides si el dictamen es bueno con un golden set de evals, y en la **sesión 8** decides qué
subagente puede correr con un modelo más barato.
