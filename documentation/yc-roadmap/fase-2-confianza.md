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

Actualización tras 2.5: ahora 4 de las 6 etiquetas son alcanzables (`multi_source`,
`single_source`, `developing`, y `corrected` — activada por
`add_story_correction`). Quedan 2 sin activar todavía (`contradictory`,
`official_statement`): la primera no tiene ninguna señal automática que la
dispare (requeriría detectar contradicciones entre fuentes, fuera de alcance
por ahora), la segunda depende de clasificar `relationship_type` con más
detalle (nota de 1.2/1.5). Ninguna de las dos necesita tocar
`classify_story_confidence` cuando llegue su turno — ya están implementadas.

**Verificado (2.1/2.4):** contra el Postgres real, una historia de 3 artículos
de la misma fuente clasificó correctamente como `developing` (no
`multi_source`, porque `source_count=1` aunque `article_count=3` — republicó,
no confirmó desde otro medio), con `sources`/`articles[].author`/`is_update`
devueltos correctamente por `GET /api/stories/{id}`.

## 2.5 Correcciones ✅ implementado (backend)

- `feedback_submitted` con `feedback_type='error_report'` — el botón "Reportar
  un error" no necesita nada nuevo del backend: el evento ya estaba permitido
  desde Fase 0.1 (`ALLOWED_EVENT_NAMES` en `analytics.py`), acepta `story_id` y
  `metadata` libre. Solo falta el botón en el frontend.
- Historial de correcciones: tabla `story_corrections` (migración
  `016_story_corrections.sql`) + `POST /api/stories/{id}/corrections` —
  registra la corrección **y** marca `stories.current_status = 'corrected'`,
  activando la etiqueta de confianza que quedó lista pero inerte en 2.4.
- Despublicar/republicar: `POST /api/stories/{id}/unpublish` y `.../republish`.
  `list_stories` excluye `current_status = 'unpublished'` por defecto;
  `get_story` lo sigue devolviendo (auditoría/administración). Republicar
  restaura `'corrected'` si la historia tiene correcciones registradas, o
  `'developing'` si no — no vuelve a un estado "no corregido" a ciegas.
- Ambos endpoints de escritura requieren la misma API key interna que
  `/api/analytics` (`require_cron_key`) — es una acción administrativa hasta
  que exista un panel editorial real (Fase 5), no una que cualquier usuario
  pueda invocar.
- Revisión humana desde administración → sigue dependiendo de Fase 5 (no hay
  UI, solo estos endpoints).

**Verificado:** 259/259 tests (14 nuevos entre `test_stories_api.py` y
endpoints de corrección/publicación), migración `016` aplicada en Docker, y
contra el Postgres real (con limpieza posterior, sin dejar datos de prueba):
una corrección real activó `confidence.level == 'corrected'`, despublicar
sacó la historia del conteo de `list_stories` (1714 → 1713) sin afectar
`get_story`, y republicar la restauró a `'corrected'` porque conservaba su
corrección — exactamente el comportamiento que se buscaba, no un reseteo
ciego a `'developing'`.

## Criterio de salida

Cualquier usuario debe poder responder: **¿por qué EcoBrief afirma esto y de dónde
obtuvo la información?**
