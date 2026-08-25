# Fase 0 — Instrumentación y línea base

**Estado actual:** no existe. No hay tabla de eventos, ni endpoint de tracking, ni panel
de métricas en `src/`. Esta es la fase de arranque real.

**Tiempo estimado:** 1 semana.

## 0.1 Analítica de producto

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

## 0.2 Panel interno de métricas

No es un dashboard elaborado todavía: un endpoint `GET /admin/metrics` (protegido con
`API_AUTH_KEY`, igual que otros endpoints admin en `src/api/security.py`) que devuelva
JSON, y una página simple en el frontend o incluso en Grafana/Metabase apuntando
directo a Postgres si prefieres no construir UI.

Métricas mínimas:

- Visitantes diarios/semanales, usuarios registrados, WAU, MAU.
- Retención D1/D7/D30 (calculable con `analytics_events` + fecha de registro).
- Briefs abiertos por usuario, historias leídas, fuentes originales abiertas.
- Costo de IA por artículo/historia (ya tienes llamadas a Groq/OpenAI en `src/llm/`;
  loguear tokens y costo por request en `collection_run_pipeline_metrics`, que ya
  existe desde `003_collection_run_pipeline_metrics.sql`).
- Artículos recopilados/descartados, duplicados detectados, historias únicas
  producidas (ya parcialmente disponible vía `story_cluster_id`).
- Errores de scraping (ya hay logging; falta agregarlo a una tabla consultable).
- Tiempo desde publicación hasta disponibilidad en el brief.

## 0.3 Métrica de valor principal (North Star)

**Historias relevantes consumidas por usuario activo por semana.**

Secundarias: minutos estimados ahorrados, % de artículos deduplicados, usuarios que
abren ≥3 briefs/semana, organizaciones con reportes recurrentes.

## Criterio de salida

No avanzar a Fase 1 (más allá de lo ya iniciado) sin poder responder con datos reales:
**¿cuántas personas usan EcoBrief, qué hacen, y cuántas regresan?**
