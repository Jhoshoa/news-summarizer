# Fase 2 — Confianza y trazabilidad

**Estado actual:** parcial en el backend (los artículos ya guardan `source`/URL), pero
no hay nada de esto expuesto como afirmación-por-afirmación ni como UI de confianza en
el frontend. Cero modelo de correcciones.

**Tiempo estimado:** 1–2 semanas. Depende de Fase 1 (necesita el modelo `Story`).

## 2.1 Fuentes visibles

Por historia: nombre del medio, enlace original, fecha de publicación, autor (si hay),
número de fuentes consultadas, indicación de fuente oficial, última verificación. La
mayoría de estos campos ya existen en `news_articles`; falta exponerlos agregados por
historia en la respuesta de `src/api/summaries.py` (o el endpoint equivalente) y
renderizarlos en el frontend.

## 2.2 Citas por afirmación

No basta con enlaces al final del resumen. Nuevas tablas:

```sql
CREATE TABLE story_claims (
  id BIGSERIAL PRIMARY KEY,
  story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
  claim TEXT NOT NULL,
  confidence VARCHAR(20) NOT NULL,
  claim_type VARCHAR(30) NULL
);

CREATE TABLE claim_evidence (
  claim_id BIGINT NOT NULL REFERENCES story_claims(id),
  article_id INTEGER NOT NULL REFERENCES news_articles(id),
  source_excerpt TEXT NULL,
  source_url TEXT NOT NULL,
  published_at TIMESTAMP NULL
);
```

Los extractos (`source_excerpt`) son para verificación **interna**, no para
republicar contenido de terceros extensamente — cuidado con derechos de autor al
mostrarlos en la UI pública; usar frases cortas, no párrafos completos.

Esto requiere un cambio en el prompt del summarizer: en vez de devolver solo texto
libre, pedirle al LLM que devuelva afirmaciones estructuradas con su artículo fuente
(similar en espíritu a como `story_deduplicator.py` ya le pide al LLM un formato JSON
estricto — reusar ese patrón de prompting).

## 2.3 Comparación de cobertura

Por historia: qué fuentes la reportaron, qué datos aparecen en todas, qué aparece en
una sola, qué se contradice, qué no está confirmado. Se deriva de `story_articles` +
`story_claims`/`claim_evidence` una vez existan.

## 2.4 Nivel de confianza (etiquetas explicables, no un score misterioso)

- Confirmado por varias fuentes.
- Reportado por una sola fuente.
- Basado en comunicado oficial.
- Información en desarrollo.
- Existen versiones contradictorias.
- Corregido después de publicación.

Se puede derivar de `story_count`/`source_count` + `relationship_type` sin necesitar
un modelo de ML adicional al inicio.

## 2.5 Correcciones

- Botón "Reportar un error" en el frontend → nuevo evento `feedback_submitted`
  (ya contemplado en Fase 0.1) con `feedback_type='error_report'`.
- Historial de correcciones: tabla `story_corrections` (story_id, reason, corrected_at,
  corrected_by).
- Posibilidad de despublicar una historia (`stories.current_status = 'unpublished'`).
- Revisión humana desde administración → depende de Fase 5.

## Criterio de salida

Cualquier usuario debe poder responder: **¿por qué EcoBrief afirma esto y de dónde
obtuvo la información?**
