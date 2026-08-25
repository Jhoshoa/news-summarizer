# Fase 0 — Instrumentación y línea base

**Estado actual: 0.1 y 0.2 implementadas y verificadas en Docker (agosto 2026).**
0.3 (North Star) sigue siendo un objetivo a monitorear con estos datos, no una tarea
de construcción aparte.

**Tiempo estimado:** 1 semana.

## 0.1 Analítica de producto — ✅ implementado

- Tabla `analytics_events` (migración `011_analytics_events.sql`, modelo `AnalyticsEvent`
  en `src/db/repository.py`).
- `POST /api/analytics/events` (`src/api/analytics.py`): batch, descarta eventos con
  nombre desconocido sin fallar el lote, nunca 500 aunque falle la DB.
- Cliente frontend `frontend/src/services/analytics.ts`: batching + debounce 2s +
  `sendBeacon` al ocultar la pestaña.
- Eventos enganchados: `brief_opened` (`HomePage.tsx`), `story_opened` y
  `source_clicked` (`ArticleDetailPage.tsx`). `category_followed`, `entity_followed`,
  `story_saved`, etc. quedan pendientes hasta que existan esas funciones (Fase 3).
- 17 tests nuevos entre backend y frontend, todos verificados contra el stack Docker
  real (evento con `session_id` real confirmado en Postgres).

Referencia histórica (spec original antes de implementar):

Eventos mínimos a registrar:

```
user_registered, onboarding_completed, brief_opened, story_opened,
source_clicked, category_followed, entity_followed, story_saved,
story_shared, alert_created, feedback_submitted, report_generated
```

Propiedades por evento: `userId`, `sessionId`, `country`, `department`, `category`,
`storyId`, `sourceId`, `device`, `timestamp`.

### Implementación sugerida (mínima, sin infraestructura nueva)

- Nueva tabla `analytics_events` en Postgres (ya tienes Postgres; no agregues Redis ni
  un servicio externo todavía — ver [no-construir-ahora.md](no-construir-ahora.md)).
  Migración `011_analytics_events.sql`.
- Un endpoint `POST /events` en `src/api/` (nuevo `analytics.py`) que el frontend llama
  de forma "fire and forget".
- Un cliente ligero en `frontend/src/` (`lib/analytics.ts`) que envuelva `fetch` y no
  bloquee la UI si falla.
- Emitir `brief_opened`, `story_opened`, `source_clicked` desde los componentes que ya
  renderizan el brief y las historias.

```sql
CREATE TABLE analytics_events (
  id BIGSERIAL PRIMARY KEY,
  event_name VARCHAR(60) NOT NULL,
  user_id INTEGER NULL REFERENCES subscribers(id),
  session_id VARCHAR(80) NULL,
  country VARCHAR(10) NULL,
  department VARCHAR(80) NULL,
  category VARCHAR(60) NULL,
  story_id VARCHAR(64) NULL,
  source_id VARCHAR(120) NULL,
  device VARCHAR(20) NULL,
  metadata JSONB NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_analytics_events_name_time ON analytics_events(event_name, created_at);
CREATE INDEX ix_analytics_events_user ON analytics_events(user_id);
```

## 0.2 Panel interno de métricas — ✅ implementado (versión mínima)

`GET /api/analytics/dashboard` (protegido con `X-API-Key`, mismo patrón que
`/api/economic-indicators/refresh`) combina en una sola respuesta:

- `product`: lo mismo que `/api/analytics/summary` (event_counts, sesiones/usuarios
  únicos) — comportamiento de usuario.
- `pipeline`: totales de `collection_runs` en la ventana (recolectados, útiles,
  descartados por calidad, deduplicados, candidatos a IA, resúmenes generados,
  duplicados evitados por IA) — eficiencia del pipeline, ya trackeada desde
  `003_collection_run_pipeline_metrics.sql`, solo se sumó una vista agregada nueva.
- `returning`: aproximación de retención por `session_id` (sesiones de la ventana
  actual que ya habían aparecido en la ventana anterior). **Limitación explícita:**
  no es retención por usuario identificado — la mayoría del tráfico es anónimo (sin
  login). Es una proxy razonable hasta que exista una cuenta de usuario real; no
  presentar esto como "retención D7" sin esta aclaración en la aplicación a YC.
- `active_subscribers`: reusa `get_subscription_count()` ya existente.

Pendiente, no bloqueante para avanzar de fase:

- Costo de IA por artículo/historia (requiere loguear tokens por request en
  `src/llm/router.py` y sumarlos a `collection_run_pipeline_metrics`).
- Errores de scraping en tabla consultable (hoy solo en logs).
- Tiempo desde publicación hasta disponibilidad en el brief.
- UI de panel en el frontend (hoy es JSON vía API; una página admin queda para
  cuando haya un usuario interno que la use a diario, no antes).

## 0.3 Métrica de valor principal (North Star)

**Historias relevantes consumidas por usuario activo por semana.**

Secundarias: minutos estimados ahorrados, % de artículos deduplicados, usuarios que
abren ≥3 briefs/semana, organizaciones con reportes recurrentes.

## Criterio de salida

No avanzar a Fase 1 (más allá de lo ya iniciado) sin poder responder con datos reales:
**¿cuántas personas usan EcoBrief, qué hacen, y cuántas regresan?**
