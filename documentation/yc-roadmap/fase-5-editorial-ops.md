# Fase 5 — Panel editorial y operaciones

**Estado actual:** no existe panel admin en el repo (`src/api/security.py` protege
endpoints con clave, pero no hay UI de administración). Esto es necesario porque no se
puede depender 100% de la automatización, especialmente para casos ambiguos de
deduplicación (Fase 1.2, nivel 7) y correcciones (Fase 2.5).

**Tiempo estimado:** en paralelo con Fase 4, priorizar lo mínimo que Fase 2.5 y 1.2
necesitan primero.

## Funciones necesarias

- Revisar historias de alta prioridad.
- Fusionar historias / separar artículos incorrectamente agrupados (acción manual
  sobre `story_articles`).
- Editar título y resumen de una historia.
- Marcar fuentes oficiales.
- Registrar correcciones (usa `story_corrections` de Fase 2.5).
- Bloquear una fuente.
- Despublicar contenido.
- Revisar feedback (de `analytics_events`/`feedback_submitted`, Fase 0 y 3.5).
- Consultar errores del scraper.
- Reprocesar un artículo.
- Ver costo de IA (de `collection_run_pipeline_metrics`, ya existe la tabla base).
- Ver historial de prompts y modelos usados.
- Comparar resultado automático vs. edición humana.

## Gestión de fuentes

Hoy las fuentes viven en `config/sources.yaml` (estático, requiere deploy para
cambiar). Evolucionar a gestión dinámica por fuente: país, ciudad/cobertura,
categorías, tipo de fuente, URL, método de extracción, frecuencia, tasa de éxito,
último scraping, confiabilidad operativa, reglas específicas, selectores
configurables, restricciones de uso.

Esto es lo que hace posible la Fase 6 (segundo país) sin reescribir código: mover de
YAML estático a una tabla `sources` editable desde el panel, con selectores igual de
configurables que hoy pero sin requerir un deploy.

## Configuración por país

```sql
CREATE TABLE country_configurations (
  country_code VARCHAR(10) PRIMARY KEY,
  timezone VARCHAR(50) NOT NULL,
  language VARCHAR(10) NOT NULL,
  regions TEXT[] NOT NULL,
  categories TEXT[] NOT NULL,
  trusted_domains TEXT[] NULL,
  official_domains TEXT[] NULL,
  stop_words TEXT[] NULL,
  entity_aliases JSONB NULL,
  date_formats TEXT[] NULL
);
```

Esta tabla es la pieza que demuestra a YC que la plataforma es replicable, no
hardcodeada para Bolivia. Priorizarla antes de intentar el segundo país (Fase 6).

## Criterio de salida

No hay un criterio numérico aquí — el criterio es que el equipo pueda operar el
producto (corregir, fusionar, bloquear fuentes) sin tocar código ni la base de datos
directamente.
