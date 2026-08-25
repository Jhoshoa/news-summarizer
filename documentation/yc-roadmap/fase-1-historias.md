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

## 1.2 Deduplicación por niveles (progresiva) — completo para lo que se puede construir ahora

De los 7 niveles, 4 quedan deliberadamente sin construir todavía porque el propio
roadmap los condiciona a cosas que aún no existen — no es trabajo pendiente
olvidado, es la secuencia que el roadmap mismo definió:

- **Nivel 4 (embeddings):** el roadmap dice explícitamente "evaluar solo si los
  niveles 1-3 no alcanzan el 85-90%". Todavía no hay una medición real de esa
  cifra (requiere correr Fase 0 sobre datos con volumen), así que construir
  embeddings ahora sería adelantarse sin evidencia — y meter un vector DB nuevo
  que el roadmap pide evitar hasta que sea necesario.
- **Nivel 5 (entidades compartidas):** depende de Fase 3.2 (extracción de
  entidades), que no existe todavía. No hay entidades que comparar.
- **Nivel 7 (revisión humana):** depende de Fase 5 (panel editorial), que no
  existe todavía. No hay dónde mostrarle casos ambiguos a un humano.

Los 4 niveles restantes (1, 2, 3, 6) sí eran construibles ahora y ya están hechos.

Orden recomendado, reusando lo existente donde aplica:

1. URL normalizada — ✅ implementado (`normalize_url`/`build_url_fingerprint` en
   `story_fingerprint.py`). Corre en `find_recent_story_match` (`repository.py`)
   antes del loop de similitud textual: si la URL normalizada de dos artículos
   coincide (mismo host sin `www.`, mismo path sin barra final, sin parámetros
   de tracking como `utm_*`/`fbclid`/`gclid`), se consideran la misma historia
   con score 1.0 y razón `url_normalized`, sin necesidad de comparar texto.
   Deliberadamente no toca `url_hash` (identidad exacta de artículo usada en
   el upsert) — es una señal nueva solo para el matching de historias, no
   cambia cuándo un artículo se trata como "ya existente" vs nuevo.
2. Título normalizado — ✅ ya existe (`normalize_story_text` en `story_fingerprint.py`).
3. Similitud textual (Jaccard de tokens + `SequenceMatcher`) — ✅ ya existe
   (`story_similarity`).
4. Embeddings — ❌ no implementado. Evaluar solo si los niveles 1-3 no alcanzan el
   85-90% del criterio de salida; no agregar un vector DB nuevo todavía, usar
   `pgvector` sobre el Postgres existente si se necesita.
5. Entidades compartidas — depende de Fase 3.2 (extracción de entidades).
6. Cercanía temporal — ✅ implementado (`temporal_proximity_factor` en
   `story_fingerprint.py`). El score de similitud textual se multiplica por un
   factor en (0.85, 1.0]: ~1.0 si los artículos son casi simultáneos, baja
   hasta 0.85 cuando la distancia temporal se acerca al borde de la ventana de
   búsqueda (`STORY_LOOKBACK_DAYS`, 3 días por defecto). Reduce falsos
   positivos de temas recurrentes con titulares parecidos (ej. encuestas
   semanales) sin afectar matches que ya eran claros por texto.
7. Revisión humana para casos ambiguos — depende de Fase 5 (panel editorial).

**Verificado:** 232/232 tests (incluye 8 tests nuevos en `test_story_fingerprint.py`
para normalización de URL y decaimiento temporal) y validación manual contra el
Postgres de desarrollo (`docker exec` con datos reales): una URL con parámetros
de tracking distintos se detectó correctamente como `url_normalized`/1.0, y el
factor temporal se aplicó con el valor exacto esperado por la fórmula.

No usar solo un umbral de embeddings: combinar con fecha, ubicación, personas,
organizaciones, tipo de evento, palabras distintivas — esto ya es parcialmente el
enfoque del prompt en `story_deduplicator.py` (reglas explícitas de "mismo hecho
verificable" en vez de solo similitud semántica), hay que extenderlo con las señales
estructuradas del punto 6.

## 1.3 Resumen consolidado ✅ implementado

`Database.get_story_sibling_articles` (`repository.py`) trae los demás artículos
activos del mismo `story_cluster_id`; `NewsSummarizerApp._attach_corroborating_articles`
(`main.py`) los adjunta a cada candidato antes de resumir, y `summarizer._build_prompt`
los incluye como sección "Otras fuentes que cubren el mismo hecho" (título + extracto,
máximo 4 fuentes adicionales para no disparar el tamaño/costo del prompt). Sigue
generándose **un solo resumen consolidado** por historia, no uno por artículo — el
prompt solo le da al modelo más contexto para escribirlo mejor.

Degrada con gracia: si `self.db` no está disponible, si el artículo no tiene
`story_cluster_id`, o si la consulta a la DB falla, el resumen se genera igual que
antes (sin la sección extra) — no hay ningún camino donde esto pueda romper el
pipeline de recolección.

**Verificado:** 239/239 tests, y contra el Postgres real: un cluster de 3 artículos
sobre el mismo hecho ("Aprehenden/Arrestan ... con más de Bs 1 millón") devolvió
correctamente los 2 artículos hermanos con su fuente al consultar por cualquiera de
los tres IDs.

## 1.4 Actualizaciones incrementales ✅ implementado (versión sin IA)

- No crear una historia nueva — ✅ ya pasaba desde 1.1 (`_upsert_story` asocia el
  artículo a la historia existente vía `story_articles` en vez de crear una fila
  `stories` nueva).
- Actualizar `last_updated_at` — ✅ ya pasaba desde 1.1.
- Determinar qué cambió y mostrárselo al usuario — ✅ nuevo: `is_meaningful_title_update`
  (`story_fingerprint.py`) compara el título del artículo nuevo contra
  `canonical_title` de la historia (mismo `SequenceMatcher` que ya usa el resto del
  dedup, umbral 0.92). Si difieren lo suficiente como para no ser solo una
  republicación, `_upsert_story` (`repository.py`) escribe
  `stories.last_update_note = "Actualización: <título nuevo>"` (columna nueva,
  migración `014_story_updates.sql`). `GET /api/stories/{id}` y `GET /api/stories`
  ya lo devuelven.
- `stories.short_summary` — ✅ nuevo: cerraba un hueco real de 1.1/1.3 (la columna
  existía pero nada la llenaba). `save_summaries` (`repository.py`) ahora también
  escribe el resumen consolidado en la historia cuando el summary trae
  `story_cluster_id`, así `GET /api/stories/{id}` deja de devolver siempre `null`.

**Deliberadamente sin IA todavía:** la nota de actualización es heurística (basada
en similitud de título), no un diff semántico generado por LLM ("la medida fue
suspendida después del anuncio inicial"). Eso evita una llamada de IA extra por
cada artículo entrante (protege el costo que mide Fase 0.2) y es honesto sobre lo
que el sistema realmente sabe. Si en el uso real esta señal resulta insuficiente,
el siguiente paso natural es que el LLM que ya genera el resumen consolidado
(1.3) también devuelva una nota de cambio explícita cuando detecte que está
resumiendo una historia con artículos nuevos desde el último resumen — no
requeriría una llamada de IA adicional, solo extender el prompt existente.

**Verificado:** 242/242 tests, migración `014` aplicada en Docker, y contra el
Postgres real (con rollback, sin dejar datos de prueba): una historia real de 1
artículo recibió una nota de actualización correcta al simular un segundo
artículo con título distinto, y `short_summary` se persistió correctamente al
llamar `save_summaries` con `story_cluster_id`.

## 1.5 Línea de tiempo ✅ implementado

`GET /api/stories/{id}` devuelve `articles` ordenados por `published_at` con
`relationship_type` (igual que desde 1.1) y ahora también `is_update` (`true` para
todo artículo que no sea el primero cronológicamente de la historia) — el timeline
básico que pedía el roadmap. Lo que falta para el timeline "completo" del roadmap
(reacciones/correcciones/confirmaciones oficiales como categorías propias, no solo
"duplicado") depende de clasificar `relationship_type` con más detalle, lo cual
requiere comparar contenido con IA — ver nota de 1.2 sobre `relationship_type` y
la idea de extender el prompt de 1.3 en vez de agregar una llamada nueva.

## Criterio de salida

- ≥85–90% de duplicados claros correctamente agrupados (medible una vez exista Fase 0).
- Cada historia conserva sus artículos originales.
- El usuario entiende qué ocurrió sin abrir diez páginas.
- El sistema muestra cuándo se actualizó la información.
- Se puede medir cuánto procesamiento redundante se evitó (costo de IA, Fase 0.2).
