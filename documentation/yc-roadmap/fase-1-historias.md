# Fase 1 — Convertir artículos en historias

**Este es el diferenciador técnico principal del producto.**

**Estado actual:** parcial. Ya existe deduplicación por fingerprint/clave canónica
(`src/processors/story_fingerprint.py`) y por IA (`src/processors/story_deduplicator.py`,
que compara tanto artículos entre sí como contra resúmenes ya existentes del día). Las
tablas `news_articles` y `news_summaries` ya tienen `story_cluster_id` (migración
`005_story_deduplication.sql`). **Lo que falta es promover eso a una entidad `Story` de
primera clase**, con timeline, tipos de relación y actualizaciones incrementales
visibles al usuario — hoy el cluster es solo una clave de agrupación interna para
descartar duplicados, no un objeto que el usuario ve evolucionar.

**Tiempo estimado:** 3–4 semanas (1–2 modelo + 2 dedup/actualizaciones).

## 1.1 Historia canónica ✅ implementado

Tablas creadas (migración `012_stories.sql`), modelos `Story`/`StoryArticle`
(`src/db/repository.py`), backfill idempotente desde `story_cluster_id`
(migración `013_stories_backfill.sql`, corrida y verificada: 1714 historias /
1725 vínculos en el Postgres de desarrollo) y endpoints de lectura
(`src/api/stories.py`): `GET /api/stories` (paginado, filtra por `category` y
`min_sources`) y `GET /api/stories/{id}` (historia + artículos ordenados por
fecha, con `relationship_type`). `upsert_articles` ahora llama a
`_upsert_story` en cada inserción nueva, así que las historias se mantienen al
día automáticamente en cada ciclo de recolección — verificado end-to-end en
Docker (build, migración, y respuesta real de los endpoints).

**Riesgo pendiente:** `_upsert_story` (el camino de escritura en vivo) solo
está verificado manualmente contra Postgres real, no hay test automatizado que
lo ejerza — los tests nuevos (`tests/test_stories_api.py`) cubren la capa API
con una DB falsa. Antes de tocar esta lógica de nuevo, agregar un test de
integración real (Postgres de test o fixture con sqlite si las migraciones lo
permiten) que inserte artículos duplicados y no duplicados y verifique
`article_count`/`source_count`.

`relationship_type` todavía no distingue `follow_up`/`reaction`/`correction`/
`official_statement` — sigue el TODO de 1.4 (requiere comparar contenido con
IA, no solo duplicado/original).

Definición de tablas de referencia:

```sql
CREATE TABLE stories (
  id VARCHAR(64) PRIMARY KEY,              -- puede derivar de story_cluster_id existente
  canonical_title VARCHAR(300) NOT NULL,
  short_summary TEXT NULL,          -- nullable: aun no se genera (ver 1.3, pendiente)
  detailed_summary TEXT NULL,
  category VARCHAR(60) NULL,
  country VARCHAR(10) NOT NULL DEFAULT 'BO',
  department VARCHAR(80) NULL,
  city VARCHAR(80) NULL,
  importance_score FLOAT NULL,
  confidence_score FLOAT NULL,
  first_published_at TIMESTAMP NOT NULL,
  last_updated_at TIMESTAMP NOT NULL,
  current_status VARCHAR(40) NOT NULL DEFAULT 'developing',
  article_count INTEGER NOT NULL DEFAULT 1,
  source_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE story_articles (
  story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
  article_id INTEGER NOT NULL REFERENCES news_articles(id),
  similarity_score FLOAT NULL,
  relationship_type VARCHAR(30) NOT NULL DEFAULT 'original_report',
  PRIMARY KEY (story_id, article_id)
);
```

`relationship_type`: `original_report | duplicate | follow_up | reaction | correction |
official_statement`. Esto es nuevo — hoy `duplicate_reason` en `news_articles` solo
distingue duplicado o no, no el tipo de relación narrativa.

## 1.2 Deduplicación por niveles (progresiva)

Orden recomendado, reusando lo existente donde aplica:

1. URL normalizada — no implementado explícitamente, agregar antes que fingerprint.
2. Título normalizado — ✅ ya existe (`normalize_story_text` en `story_fingerprint.py`).
3. Similitud textual (Jaccard de tokens + `SequenceMatcher`) — ✅ ya existe
   (`story_similarity`).
4. Embeddings — ❌ no implementado. Evaluar solo si los niveles 1-3 no alcanzan el
   85-90% del criterio de salida; no agregar un vector DB nuevo todavía, usar
   `pgvector` sobre el Postgres existente si se necesita.
5. Entidades compartidas — depende de Fase 3.2 (extracción de entidades).
6. Cercanía temporal — fácil de añadir, falta.
7. Revisión humana para casos ambiguos — depende de Fase 5 (panel editorial).

No usar solo un umbral de embeddings: combinar con fecha, ubicación, personas,
organizaciones, tipo de evento, palabras distintivas — esto ya es parcialmente el
enfoque del prompt en `story_deduplicator.py` (reglas explícitas de "mismo hecho
verificable" en vez de solo similitud semántica), hay que extenderlo con las señales
estructuradas del punto 6.

## 1.3 Resumen consolidado

Regla: la IA resume la historia agrupada, no cada artículo duplicado por separado.
Hoy `summarizer.py` corre después del dedup, así que el costo redundante ya se evita en
parte; falta que el resumen use explícitamente todos los artículos del cluster como
contexto (multi-fuente) en vez de resumir solo el primero.

## 1.4 Actualizaciones incrementales

Cuando llega un artículo nuevo sobre un cluster existente:

- No crear una historia nueva — asociarla a la existente vía `story_articles`.
- Determinar qué cambió (diff de resumen, nuevo dato).
- Actualizar `detailed_summary` y `last_updated_at`.
- Mostrar el cambio al usuario: "Actualización: la medida fue suspendida después del
  anuncio inicial."

Esto requiere un paso nuevo en el pipeline (`src/processors/`) que, en vez de solo
descartar duplicados, decida entre `crear historia` / `actualizar historia existente`.

## 1.5 Línea de tiempo

Cada historia importante muestra: primer reporte, confirmación oficial, nuevos datos,
reacciones, correcciones, resultado conocido. Se deriva directamente de
`story_articles.relationship_type` ordenado por `news_articles.published_at`.

## Criterio de salida

- ≥85–90% de duplicados claros correctamente agrupados (medible una vez exista Fase 0).
- Cada historia conserva sus artículos originales.
- El usuario entiende qué ocurrió sin abrir diez páginas.
- El sistema muestra cuándo se actualizó la información.
- Se puede medir cuánto procesamiento redundante se evitó (costo de IA, Fase 0.2).
