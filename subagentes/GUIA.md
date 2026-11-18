# Guía L6 · Orquestador con 2 subagentes especializados

> **AIENG01 · Sesión 6** · Esta es la guía completa del lab, la misma que en el Hub. Se abre sola en vista previa
> al entrar al lab. Para copiar un comando: selecciónalo en la vista previa y usa Ctrl+C (Cmd+C en Mac), o abre la
> guía web (con su botón «Copiar») desde el Hub, en la Sesión 6 de tu currículum: https://hub.bootcamp.institute/lms/student/curriculum
>
> Cada paso empieza con `cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate`: funciona en cualquier
> terminal nueva. En la terminal, `bootcamp-status` te dice en qué paso vas.

## Contenido

1. L6 · Orquestador con 2 subagentes especializados
2. Paso 1: Entorno y verificación de partida
3. Paso 2: Un subagente, solo
4. Paso 3: El orquestador, delegar y sintetizar
5. Paso 4: Subagentes en paralelo, lo implementas tú
6. Paso 5: Lo mismo con el Agent SDK
7. Paso 6: Costo, cuándo sí y cuándo no, y cierre

## L6 · Orquestador con 2 subagentes especializados

> **AIENG01 · Sesión 6** · En clase: **60 min** (pasos 1 a 6) · Extensión opcional, en casa: el reto del
> paso 6.

### Contexto

Llega a PagosYa un reclamo que mezcla todo: un doble cobro, una transferencia retenida y una amenaza de
cancelar el plan. Un solo agente con todas las herramientas puede resolverlo, pero su contexto se llena de
movimientos crudos y fragmentos de políticas, y se le mezclan los roles. Hoy lo resuelves con el patrón
**orquestador-trabajadores**: un orquestador que planea y delega, y dos subagentes especializados, cada uno
con **su contexto limpio, sus herramientas y su formato de entrega**.

> Pregunta ancla: ¿cuándo vale la pena pagar varios agentes en lugar de uno?

### Objetivos de aprendizaje

- Diseñar subagentes con rol, herramientas propias (mínimo privilegio) y un formato de entrega.
- Construir el orquestador a mano: una herramienta `delegar`, tareas autocontenidas y síntesis.
- Lanzar subagentes en paralelo y aislar sus fallas (lo implementas tú).
- Hacer lo mismo con `agents=` del Claude Agent SDK y comparar.
- Medir el costo: tokens por agente.

### Estructura

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

### Tiempos en clase

| Paso | Qué haces | Minutos |
|---|---|---|
| 1 | Entorno y verificación de partida | 5 |
| 2 | Un subagente, solo | 8 |
| 3 | El orquestador: delegar y sintetizar | 12 |
| 4 | Subagentes en paralelo: **lo implementas tú** | 15 |
| 5 | Lo mismo con el Agent SDK (`agents=`) | 12 |
| 6 | Costo, cuándo sí y cuándo no, y cierre | 8 |

### Conexión con el curso

Sesión 6 · Orquestación multi-agente. Tu proyecto integrador exige al menos un subagente. En la
**sesión 7** mides si el dictamen es bueno con un golden set de evals, y en la **sesión 8** decides qué
subagente puede correr con un modelo más barato.

---

## Paso 1: Entorno y verificación de partida

### Objetivo
Dejar el workspace del L6 listo y ver qué parte ya funciona.

### Instrucciones

#### 1.1 Entorno virtual y dependencias

Claude por **Amazon Bedrock** con las credenciales del workspace, Claude Haiku 4.5. Se instalan el SDK de
Anthropic (orquestador a mano) y el Claude Agent SDK (paso 5).

```bash
cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **`python3` y `python`.** Fuera del entorno virtual el sistema solo tiene `python3` (no hay `python` ni `pip`):
> por eso el entorno se crea con `python3 -m venv .venv`. Con el entorno activo (verás `(.venv)` en el prompt),
> `python` y `pip` son los del `.venv`, y el resto de la guía usa `python`.
>
> **Terminal nueva.** Toda terminal nueva abre en `/workshop` y con el entorno desactivado: ahí `python` da
> «command not found». Por eso cada paso empieza con `cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate`; si sigues en la
> misma terminal, no cambia nada.

#### 1.2 Verificación de partida

```bash
python verificar.py
```

Vas a ver `VERIFICACIÓN L6: 5/8`. Las 3 fallas son de `en_paralelo`, tu trabajo del paso 4. Con el starter
el orquestador igual funciona: delega en serie.

### Criterio de éxito
- [ ] `pip install` sin errores y `verificar.py` en 5/8

---

## Paso 2: Un subagente, solo

### Objetivo
Entender qué es un subagente antes de orquestarlo: un loop con su propio contexto, rol y herramientas.

### Conceptos clave

| Pieza del subagente | En `subagentes.py` | Por qué |
|---|---|---|
| Rol | `system` | Qué es y qué NO hace (el investigador no conoce políticas) |
| Herramientas | `herramientas` | Mínimo privilegio: solo las suyas, y solo lectura |
| Formato de entrega | `FORMATO` | Hechos verificados, cortos; nada de recomendaciones |
| Contexto propio | `correr_subagente()` | Sus búsquedas no ensucian el contexto del orquestador |

### Instrucciones

```bash
cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate
python subagentes.py investigador_cuenta "Revisa los cargos del plan Pro y las transferencias retenidas de laura.gomez en septiembre y octubre de 2026"
```

Lee la traza: `[investigador_cuenta] [tool] consultar_movimientos(...)`, cuántas vueltas y tokens usó, y un
informe de viñetas con IDs (`M-5101`, `M-5102`, `M-5140`). Prueba también el experto:

```bash
python subagentes.py experto_politicas "¿Qué dicen las políticas sobre un cobro duplicado del plan Pro y sobre una transferencia retenida por antifraude?"
```

### Criterio de éxito
- [ ] Cada subagente responde dentro de su rol: uno con IDs, el otro con fuentes `[archivo#sección]`

---

## Paso 3: El orquestador, delegar y sintetizar

### Objetivo
Correr el patrón orquestador-trabajadores y leer cómo reparte el trabajo.

### Conceptos clave

| Decisión | En `orquestador.py` |
|---|---|
| El orquestador no tiene herramientas de datos | Solo `delegar`: no puede «hacerlo él mismo» |
| Tareas autocontenidas | El subagente no ve la conversación: la tarea lleva cliente, qué buscar y para qué |
| Delegar en paralelo | La descripción de `delegar` pide varias llamadas en el mismo turno si son independientes |
| Fallas como dato | Si un subagente falla, el orquestador recibe `is_error` y decide |

### Instrucciones

```bash
cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate
python orquestador.py
```

En la traza:
1. `[orquestador] vuelta 1: delega 2 tarea(s) → investigador_cuenta, experto_politicas` (o en dos vueltas: anótalo).
2. Lo que hace cada subagente, con su prefijo.
3. `informes recibidos en …s`: con el starter es la **suma** de los dos tiempos.
4. El DICTAMEN con «Qué pasó», «Qué dice la política» y «Acciones recomendadas», y la línea `[tokens]`
   por agente.

Lee la **tarea** que el orquestador le escribió a cada subagente (está en la traza del subagente): ¿es
autocontenida? ¿Dice para qué la necesita?

### Criterio de éxito
- [ ] El dictamen cita los IDs del investigador y las fuentes del experto
- [ ] Sabes cuántos tokens gastó cada agente

---

## Paso 4: Subagentes en paralelo, lo implementas tú

### Objetivo
Que dos tareas independientes tarden lo que la más lenta, no la suma, y que una falla no tumbe a la otra.

### Instrucciones

#### 4.1 Implementa `en_paralelo`

Abre `paralelo.py`. El docstring trae las 3 reglas: concurrencia con tope, mismo orden y fallas aisladas.
Reemplaza la línea marcada con `TODO paso 4`.

#### 4.2 Verifica

```bash
cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate
python verificar.py
```

Itera hasta ver `VERIFICACIÓN L6: 8/8`.

#### 4.3 Compara los tiempos

```bash
python orquestador.py
```

Compara la línea `informes recibidos en …s` con la del paso 3: si el orquestador delegó las dos tareas en el
mismo turno, ahora tarda lo que el subagente más lento.

### Hints progresivos

1. *(metacognitivo)* ¿Qué tiene que pasar con la excepción de una tarea para que no llegue al `map`?
2. *(conceptual)* Envuelve cada tarea en una función que nunca lanza: devuelve `{"ok": ...}`.
3. *(procedimental)* `with ThreadPoolExecutor(max_workers=max_concurrencia) as pool:`
4. *(solución parcial)* `pool.map(una, tareas)` devuelve los resultados en el orden de entrada.
5. *(bottom-out)* Pídele al facilitador la solución de referencia y compárala con la tuya.

### Criterio de éxito
- [ ] `verificar.py` en 8/8
- [ ] Con dos delegaciones en el mismo turno, el tiempo es el del subagente más lento

---

## Paso 5: Lo mismo con el Agent SDK

### Objetivo
Ver qué te da el SDK de fábrica para orquestar, y qué sigue siendo decisión tuya.

### Conceptos clave

| A mano (`orquestador.py`) | Con el SDK (`orquestador_sdk.py`) |
|---|---|
| Herramienta `delegar` | Herramienta `Agent` del agente principal |
| `SUBAGENTES` + `correr_subagente()` | `agents={nombre: AgentDefinition(...)}` |
| Herramientas por subagente | `AgentDefinition(tools=[...])` |
| `en_paralelo` | El SDK corre en paralelo las delegaciones del mismo turno |
| El orquestador no tiene datos | `tools=["Agent"]` + un hook que niega las herramientas de datos al principal |

### Instrucciones

```bash
cd /workshop/aieng01/lab-06-orquestacion-multiagente/workspace && source .venv/bin/activate
python orquestador_sdk.py
```

La traza marca quién habla: `[orquestador] [tool] Agent investigador_cuenta`, luego `[subagente] [tool]
mcp__pagosya__...`, y al final el dictamen y la línea `[resultado]` con turnos y costo.

Lee `orquestador_sdk.py`: los **mismos** roles y herramientas de `subagentes.py`, sin loop propio. Lo que
no cambia: la calidad del dictamen depende de cómo describes a cada subagente y de las tareas que el
orquestador escribe.

### Criterio de éxito
- [ ] El orquestador del SDK delega en los dos subagentes y entrega el dictamen
- [ ] Puedes señalar qué parte de `orquestador.py` reemplaza cada opción

---

## Paso 6: Costo, cuándo sí y cuándo no, y cierre

### Cuándo sí y cuándo no

| Vale la pena varios agentes | Mejor uno solo |
|---|---|
| Subtareas independientes que pueden ir en paralelo | Pasos que dependen uno del otro, en secuencia |
| Mucha información cruda que no debe llenar el contexto principal | Poco contexto: cabe todo en uno |
| Roles con permisos distintos (datos contra políticas) | Mismas herramientas para todo |
| Valor de la tarea que justifica varias veces los tokens | Tareas baratas y frecuentes |

Mira tu línea `[tokens]`: el sistema completo gastó varias veces lo que un solo agente. Esa es la cuenta
que tienes que justificar.

### Qué aprendiste

- **Diseñar** subagentes: rol, herramientas propias de solo lectura y formato de entrega.
- **Orquestar** con una herramienta `delegar` y tareas autocontenidas.
- **Paralelizar** y aislar fallas.
- **Comparar** el patrón a mano con `agents=` del SDK.

### Reto opcional, en casa

Agrega un tercer subagente `redactor_respuesta` que, con el dictamen, escriba el mensaje para la cliente
(tono empático, sin prometer lo que la política no permite). ¿Lo pondrías en paralelo o en secuencia? ¿Por qué?
Y para tu proyecto integrador: define cuál es tu subagente y qué contexto le ahorra al agente principal.

### Conexión con el curso

**Sesión 7 · Confiabilidad**: ¿cómo sabes si el dictamen es bueno? Un golden set de reclamos con su dictamen
esperado, guardrails de entrada y salida, y trazas para depurar.
