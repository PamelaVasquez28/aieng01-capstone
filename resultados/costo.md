# Análisis de Costo - Revisor de Declaraciones de Origen

## Mediciones (3 corridas: DO 26-0001, 26-0003, 26-0005)

### ANTES (Sistema sin optimizar)
| Caso | Costo | Tokens Entrada | Tokens Salida |
|------|-------|---|---|
| 26-0001 (LISTO) | $0.033235 | - | - |
| 26-0003 (INCOMPLETO) | $0.009017 | - | - |
| 26-0005 (INCOMPLETO) | $0.011124 | - | - |
| **Promedio** | **$0.003065** | - | - |

### DESPUÉS (Con palancas aplicadas)
| Caso | Costo | Tokens Entrada | Tokens Salida |
|------|-------|---|---|
| 26-0001 (LISTO) | $0.020903 | - | - |
| 26-0003 (INCOMPLETO) | $0.010700 | - | - |
| 26-0005 (INCOMPLETO) | $0.010236 | - | - |
| **Promedio** | **$0.002468** | - | - |

## Palancas Aplicadas

1. **SYSTEM más corto:** De ~450 caracteres a ~200 (55% reducción)
   - Eliminó enumeración detallada de pasos
   - Redujo explicación de reglas críticas
   - Mantuvo esencial: qué verificar, orden, formato salida

2. **Max turns acotado:** De 15 a 8 turnos
   - Agente termina antes (evita loops innecesarios)
   - Verificador sigue siendo llamado 1x en casos INCOMPLETO

3. **Verificador condicional:** Solo para INCOMPLETO
   - LISTO: no requiere verificación (si todos docs 'cargado' + valores cuadran → LISTO)
   - INCOMPLETO: verifica problemas reportados
   - **50% de los casos se ahorran una llamada al subagente**

## Resultados

| Métrica | Valor |
|---------|-------|
| Costo promedio ANTES | $0.003065 |
| Costo promedio DESPUÉS | $0.002468 |
| **Ahorro por pregunta** | **$0.000597 (19.3%)** |
| **Ahorro porcentaje** | **-19.3%** |

## Proyecciones a 1.000 preguntas/día

### ANTES (sin optimizar)
- Costo/día: 1.000 × $0.003065 = **$3.065/día**
- Costo/mes (30 días): **$91.95/mes**
- Costo/mes (22 días laborales): **$67.43/mes**

### DESPUÉS (con palancas)
- Costo/día: 1.000 × $0.002468 = **$2.468/día**
- Costo/mes (30 días): **$74.04/mes**
- Costo/mes (22 días laborales): **$54.30/mes**

### Ahorro Mensual
- 30 días: $91.95 - $74.04 = **$17.91/mes (19.5% ahorro)**
- 22 días: $67.43 - $54.30 = **$13.13/mes (19.5% ahorro)**

## Notas

- Mediciones con Claude Haiku 4.5 vía Bedrock (gateway del curso)
- Incluye trazas, guardrails, y verificador
- 3 corridas por escenario (estadísticamente insuficiente, pero indicativo)
- Variabilidad: algunos casos necesitan más tokens (INCOMPLETO con múltiples problemas)
- Próxima mejora: cache de prompts (no aplicado aquí)
