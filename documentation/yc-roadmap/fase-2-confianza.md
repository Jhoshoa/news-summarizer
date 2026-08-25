# Fase 2 — Confianza y trazabilidad

**Estado actual:** parcial en el backend (los artículos ya guardan `source`/URL), pero
no hay nada de esto expuesto como afirmación-por-afirmación ni como UI de confianza en
el frontend. Cero modelo de correcciones.

**Tiempo estimado:** 1–2 semanas. Depende de Fase 1 (necesita el modelo `Story`).

## 2.1 Fuentes visibles ✅ implementado (backend)

`GET /api/stories/{id}` ahora devuelve, por historia: `sources` (lista de medios
distintos que la cubrieron), y por cada artículo en `articles`: medio, URL, fecha
de publicación, autor (si existe), y `is_update`. `source_count`/`article_count`
(número de fuentes/artículos consultados) y `last_updated_at` (última
verificación) ya existían desde Fase 1.1. Falta la parte de frontend
(renderizarlo) — no incluida en este backend-only pass.

## 2.2 Citas por afirmación ✅ implementado (backend)

No basta con enlaces al final del resumen — ahora el prompt del summarizer
(`SYSTEM_PROMPT`/`_build_prompt` en `summarizer.py`) pide, además del resumen,
hasta 3 "claims" (afirmaciones puntuales y verificables) con `confidence`
(`multi_source`/`single_source`/`official_statement`), `claim_type`, y el
`article_id` + extracto corto (<160 caracteres, cuidando derechos de autor)
de la fuente exacta que la respalda.

**La pieza de seguridad real de esta feature:** el LLM nunca decide qué URL se
guarda. `_normalize_claims`/`_valid_evidence_articles` construyen una lista
blanca con el artículo principal y sus fuentes corroborantes (Fase 1.3) —
cada `article_id` que el modelo devuelve se valida contra esa lista; si
inventa un ID que no está ahí, la afirmación se descarta entera (mejor
ninguna cita que una inventada). Verificado con un test que simula justo eso
(`test_parse_response_discards_claim_with_invented_article_id_but_keeps_summary`).

`Database._replace_story_claims` (`repository.py`) persiste esto en
`story_claims`/`claim_evidence` (migración `015_story_claims.sql`) —
**reemplaza**, no acumula: cada corrida de resumen refleja las afirmaciones
vigentes, no un historial creciente de versiones viejas de la misma historia.
`GET /api/stories/{id}` ya expone `claims`. Falta el frontend.

Esquema real (migración `015_story_claims.sql`, con `id`/`created_at` y
`ON DELETE CASCADE` en la evidencia para que reemplazar sea una operación limpia):

```sql
CREATE TABLE story_claims (
  id BIGSERIAL PRIMARY KEY,
  story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
  claim TEXT NOT NULL,
  confidence VARCHAR(20) NOT NULL,
  claim_type VARCHAR(30) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE claim_evidence (
  id BIGSERIAL PRIMARY KEY,
  claim_id BIGINT NOT NULL REFERENCES story_claims(id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES news_articles(id),
  source_excerpt TEXT NULL,
  source_url TEXT NOT NULL,
  published_at TIMESTAMP NULL
);
```

Los extractos (`source_excerpt`) son para verificación **interna**, no para
republicar contenido de terceros extensamente — cuidado con derechos de autor al
mostrarlos en la UI pública; usar frases cortas, no párrafos completos. El límite
de 160 caracteres en `CLAIM_EXCERPT_MAX_CHARS` (`summarizer.py`) lo hace cumplir
en código, no solo como convención.

**Verificado:** 254/254 tests (10 nuevos entre `summarizer.py` y el flujo de
persistencia), migración `015` aplicada en Docker, y contra el Postgres real
(con rollback donde correspondía, sin dejar datos de prueba): una segunda
generación de claims reemplazó correctamente a la primera sin acumular filas,
un claim con `article_id` inventado se descartó solo, y `GET /api/stories/{id}`
devuelve `claims` con su evidencia real.

## 2.3 Comparación de cobertura

Por historia: qué fuentes la reportaron, qué datos aparecen en todas, qué aparece en
una sola, qué se contradice, qué no está confirmado. Se deriva de `story_articles` +
`story_claims`/`claim_evidence` una vez existan.

## 2.4 Nivel de confianza (etiquetas explicables, no un score misterioso) ✅ implementado

`src/processors/story_confidence.py` — `classify_story_confidence` deriva una de
las 6 etiquetas desde `source_count`, `article_count`, `current_status` y
`relationship_type` de los artículos, sin modelo de ML. Se expone como
`confidence: {level, label}` en `GET /api/stories` y `GET /api/stories/{id}`.

Hoy, con los datos que existen, solo 3 de las 6 etiquetas son alcanzables en la
práctica (`multi_source`, `single_source`, `developing`) — las otras 3
(`corrected`, `contradictory`, `official_statement`) están implementadas y
listas, pero nada todavía asigna `current_status='corrected'`/`'contradictory'`
ni `relationship_type='official_statement'`. Se activan solas en cuanto Fase 2.5
(correcciones) o una clasificación más fina de `relationship_type` empiecen a
escribir esos valores — no van a requerir tocar esta función.

## 2.5 Correcciones

- Botón "Reportar un error" en el frontend → nuevo evento `feedback_submitted`
  (ya contemplado en Fase 0.1) con `feedback_type='error_report'`.
- Historial de correcciones: tabla `story_corrections` (story_id, reason, corrected_at,
  corrected_by).
- Posibilidad de despublicar una historia (`stories.current_status = 'unpublished'`).
- Revisión humana desde administración → depende de Fase 5.

**Verificado:** 249/249 tests (7 nuevos para `classify_story_confidence` +
2 actualizados en `test_stories_api.py`), backend y cron-job reconstruidos y
reiniciados en Docker, y contra el Postgres real: una historia de 3 artículos
de la misma fuente clasificó correctamente como `developing` (no
`multi_source`, porque `source_count=1` aunque `article_count=3` — republicó,
no confirmó desde otro medio), con `sources`/`articles[].author`/`is_update`
devueltos correctamente por `GET /api/stories/{id}`.

## Criterio de salida

Cualquier usuario debe poder responder: **¿por qué EcoBrief afirma esto y de dónde
obtuvo la información?**
