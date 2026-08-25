# Alineación con la propuesta Green Tech

Fuente: `documentation/version-1/` — `documento-ejecutivo.md`, `anexo-tecnico.md`,
`informe/resumen.tex` (el documento que ganó el concurso Green Tech, USD 280).

## Por qué este archivo existe

El roadmap de YC ([README.md](README.md)) fue escrito antes de leer a fondo
`documentation/version-1/`. Esa carpeta contiene la propuesta que ya validó el
proyecto externamente. Este archivo deja explícito cómo se conectan ambas cosas para
que ninguna fase futura contradiga la identidad que ya ganó.

## El mensaje central que no se debe perder

> EcoBrief Bolivia usa IA no para producir más ruido, sino para reducirlo.

Cuatro niveles de "desperdicio digital" que el proyecto ataca (documento ejecutivo,
sección 2): usuario (tiempo), datos (MB), IA (llamadas redundantes), confianza
(contenido no trazable). El roadmap YC agrega un quinto y sexto nivel de valor
(personalización, ingresos B2B) pero **no debe abandonar los primeros cuatro**.

## Qué ya existe y que el roadmap YC debe reusar, no duplicar

| Activo Green Tech ya construido | Dónde vive | Cómo se conecta con el roadmap YC |
| --- | --- | --- |
| Página de Impacto + `/api/impact-metrics` | `src/api/impact_metrics.py`, `Database.get_impact_metrics` | Es la base de la "métrica de valor" ambiental. [Fase 0](fase-0-analitica.md) agrega `analytics_events` (comportamiento de usuario) **al lado** de esto, no en su lugar. |
| Fórmulas de ahorro (`paginas_evitadas`, `minutos_ahorrados`, `mb_ahorrados`, `tasa_reduccion`) | `Database.IMPACT_MINUTES_PER_ARTICLE`, `IMPACT_MB_PER_PAGE` en `src/db/repository.py` | Reusar literalmente estas fórmulas en cualquier reporte B2B ([Fase 4](fase-4-b2b.md)) en vez de inventar métricas nuevas — son las que ya se presentaron y ganaron. |
| Deduplicación por fingerprint + histórica | `story_fingerprint.py`, `story_deduplicator.py`, migración 005 | Es la pieza técnica central del pitch ganador ("IA aplicada después de deduplicar"). [Fase 1](fase-1-historias.md) la extiende a un modelo `Story` completo — el criterio de salida de Fase 1 (85-90% de duplicados agrupados) es directamente la métrica que ya se mostró en el concurso. |
| Trazabilidad a fuente original | Campos `source`, `url` en `news_articles`, ya mostrados en Detalle de artículo | [Fase 2](fase-2-confianza.md) (citas por afirmación, comparación de cobertura) es una extensión directa de "conserva enlace a la fuente original" — mismo principio, más estructurado. |
| Roadmap técnico propio ya esbozado (anexo técnico, sección 14) | — | Ya proponía: detección por entidades, planes de suscripción para organizaciones/analistas, panel institucional de monitoreo, integración de boletines oficiales. Esto es casi exactamente [Fase 3.2](fase-3-personalizacion.md) (entidades), [Fase 4](fase-4-b2b.md) (B2B) y la idea de fuentes oficiales de [Fase 2.1](fase-2-confianza.md). El roadmap YC no es una dirección nueva — es la continuación del roadmap que el equipo ya había planteado, con más disciplina de producto (medir antes de construir) y una capa de negocio explícita. |

## Modelos de IA: el documento quedó desactualizado, no la estrategia

El anexo técnico documenta `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` y
`llama-3.1-70b-versatile` como modelos Groq vigentes. Groq los deprecó (confirmado
contra su endpoint `/models` en agosto 2026); ver el fix ya aplicado en
`src/llm/client.py`. La estrategia del documento (Groq/DeepSeek como proveedores de
bajo costo, modelos grandes solo cuando la calidad lo justifique, arquitectura con
cliente LLM abstraído para poder cambiar de proveedor) sigue siendo válida y es la
que ya sigue `src/llm/router.py`. Solo hay que mantener los nombres de modelo al día
— un riesgo operativo real que [Fase 0](fase-0-analitica.md) debería vigilar (alerta
cuando el LLM falla).

## Qué significa esto en la práctica para cada fase nueva

- **Fase 0 (analítica):** no compite con el panel de Impacto — lo complementa. Al
  construir el panel interno de métricas (0.2), mostrar ambos paneles juntos:
  eficiencia del pipeline (ya existe) + comportamiento de usuario (nuevo).
- **Fase 1 (historias):** el criterio de éxito ya tiene un antecedente concreto que
  se puede citar en la aplicación a YC ("ya demostramos deduplicación real en
  producción, ganamos un concurso con eso").
- **Fase 2 (confianza):** es la misma promesa Green Tech de trazabilidad, llevada a
  nivel de afirmación individual en vez de solo artículo.
- **Fase 3-4 (personalización/B2B):** siguen literalmente el roadmap técnico que el
  propio anexo técnico ya proponía (sección 14, mediano/largo plazo).
- **Cualquier fase nueva:** si una función agrega llamadas a IA sin haber filtrado,
  deduplicado y rankeado antes, no es fiel al proyecto que ganó el concurso — revisar
  contra `documentation/version-1/anexo-tecnico.md` sección 6 antes de construirla.

## Para la narrativa de YC

[narrativa-yc.md](narrativa-yc.md) ya menciona el premio Greentech como señal de
validación. Vale la pena ser más específico: no fue solo un premio a una idea, fue un
premio a un **prototipo funcional con arquitectura, tests y métricas reales** — eso
es exactamente lo que YC pesa más que la idea sola. La frase corta de
`documento-ejecutivo.md` ("EcoBrief Bolivia usa IA no para producir más ruido, sino
para reducirlo") es un buen complemento a la frase corta de YC ("the local
intelligence layer for Latin America") — la primera explica la disciplina técnica,
la segunda explica la ambición de mercado. Usar ambas.
