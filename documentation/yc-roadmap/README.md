# EcoBrief — Roadmap hacia YC

Este directorio traduce el plan estratégico recibido en fases ejecutables, ajustadas a lo
que el código de este repo ya tiene hoy (agosto 2026). Cada fase tiene su propio archivo con:
tareas, estado actual (qué ya existe vs. qué falta), modelo de datos si aplica, y criterio de
salida.

## Índice

| Fase | Archivo | Objetivo |
| --- | --- | --- |
| 0 | [fase-0-analitica.md](fase-0-analitica.md) | Instrumentar el producto antes de seguir construyendo |
| 1 | [fase-1-historias.md](fase-1-historias.md) | Artículos → historias canónicas (diferenciador técnico) |
| 2 | [fase-2-confianza.md](fase-2-confianza.md) | Trazabilidad, fuentes visibles, correcciones |
| 3 | [fase-3-personalizacion.md](fase-3-personalizacion.md) | Onboarding, entidades seguidas, brief por email |
| 4 | [fase-4-b2b.md](fase-4-b2b.md) | EcoBrief Intelligence (workspaces, monitores, informes, cobro) |
| 5 | [fase-5-editorial-ops.md](fase-5-editorial-ops.md) | Panel editorial y gestión de fuentes |
| 6 | [fase-6-expansion.md](fase-6-expansion.md) | Segundo país |
| — | [no-construir-ahora.md](no-construir-ahora.md) | Lista negra explícita para esta etapa |
| — | [orden-ejecucion.md](orden-ejecucion.md) | Orden exacto, tiempos, y checklist semanal |
| — | [narrativa-yc.md](narrativa-yc.md) | Problema/solución/cuña/expansión/ventaja para la aplicación |
| — | [alineacion-green-tech.md](alineacion-green-tech.md) | Cómo se conecta este roadmap con la propuesta que ya ganó Green Tech |

## Decisión estratégica (resumen)

EcoBrief pasa de ser "una colección de resúmenes de noticias" a ser **la capa de
inteligencia local de Latinoamérica**, con dos productos:

- **EcoBrief Personal** (gratis): brief diario personalizado, historias deduplicadas,
  seguimiento de temas/entidades. Objetivo: distribución, uso recurrente, datos de
  comportamiento.
- **EcoBrief Intelligence** (pago): monitoreo de temas/empresas/autoridades, alertas
  regulatorias/reputacionales, informes automáticos, comparación entre fuentes,
  exportación para equipos. Objetivo: ingresos.

Bolivia es el mercado y laboratorio inicial. Un segundo país (fase 6) prueba
replicabilidad — esa es la métrica que le importa a YC ("Bolivia tomó meses porque
construimos la plataforma; el segundo país tomó siete días").

No se construye todavía: denuncias anónimas, rankings, red social, comentarios
públicos, app móvil, blockchain, IA propia, chatbot genérico. Ver
[no-construir-ahora.md](no-construir-ahora.md).

## Estado actual del repo (línea base, ago-2026)

Lo que **ya existe** y sobre lo que hay que construir, no rehacer:

- Recolección: scraper (`src/collectors/scraper.py`) + NewsAPI (`newsapi_collector.py`),
  además de indicadores económicos (dólar BCB) y clima.
- Deduplicación por fingerprint de contenido y clave canónica
  (`src/processors/story_fingerprint.py`, `story_deduplicator.py`), con
  `canonical_key`, `content_fingerprint`, `story_cluster_id`, `duplicate_of_article_id`
  ya en el esquema (migración `005_story_deduplication.sql`). Esto es una base parcial
  de la Fase 1, **no un modelo de Historia completo** (no hay tabla `stories`,
  ni timeline, ni relationshipType, ni actualizaciones incrementales visibles al usuario).
- Clasificación, ranking, resumen y reescritura (`classifier.py`, `ranker.py`,
  `summarizer.py`, `rewriter.py`).
- Suscriptores con preferencias básicas (`004_subscriber_preferences.sql`: frecuencia,
  hora preferida, consentimiento) y email de suscriptor (`006_subscriber_email.sql`).
- Distribución por Email, WhatsApp y Telegram (`src/distributors/`).
- Jobs asíncronos de refresco de resumen (`009_summary_refresh_jobs.sql`).
- Frontend en React/Vite (`frontend/`) con página de suscripción.

Lo que **no existe todavía** (confirmado por ausencia en `src/` y `migrations/`):
analítica de producto/eventos, panel interno de métricas, modelo `Story`/`StoryArticle`
con timeline y tipos de relación, `StoryClaim`/`ClaimEvidence`, extracción de entidades,
onboarding de usuario, seguimiento de entidades/temas, workspaces, monitores, alertas
inteligentes, informes automáticos B2B, facturación, panel editorial/admin de fuentes,
configuración multi-país (`CountryConfiguration`).

Esto confirma que Fase 0 y buena parte de Fase 1 son el punto de partida correcto: no
hay visibilidad de uso todavía, y el modelo de datos de "historia" está a medio camino.

Ya existe también un panel de **impacto ambiental** (`GET /api/impact-metrics`,
`Database.get_impact_metrics` en `src/db/repository.py`, página "Impacto" del
frontend) que calcula `paginas_evitadas`, `minutos_ahorrados`, `mb_ahorrados` y
`tasa_reduccion` a partir del pipeline real. **Fase 0 (analítica de producto) es
complementaria a esto, no un reemplazo**: el panel de impacto mide eficiencia del
pipeline (lo que ya ganó Green Tech); `analytics_events` mide comportamiento de
usuario (lo que hace falta para YC). Ver [alineacion-green-tech.md](alineacion-green-tech.md).

## Alineación con la propuesta Green Tech

Antes de seguir agregando fases, se leyó `documentation/version-1/` (documento
ejecutivo, anexo técnico e informe LaTeX del concurso Green Tech que este mismo
proyecto ganó — USD 280). El mensaje central de esa propuesta es:

> EcoBrief Bolivia usa IA no para producir más ruido, sino para reducirlo.

Este roadmap **no reemplaza esa identidad, la extiende**. El roadmap YC agrega
personalización, confianza/trazabilidad y B2B — pero cualquier feature nueva debe
seguir la misma disciplina que ya premiaron: filtrar y deduplicar antes de llamar a
IA, no volver a sumar ruido por sumar features. Ver el detalle en
[alineacion-green-tech.md](alineacion-green-tech.md).
