# Fase 3 — Personalización que genere recurrencia

**Estado actual:** hay una base de suscriptores con frecuencia/hora preferida/consentimiento
(`004_subscriber_preferences.sql`) y canales Email/WhatsApp/Telegram ya implementados
(`src/distributors/`). **No existe** onboarding guiado, seguimiento de entidades, ni
brief realmente personalizado por temas — hoy el brief es el mismo contenido para todos
los suscriptores, filtrado como mucho por frecuencia/hora, no por intereses.

**Tiempo estimado:** ~4 semanas (1 onboarding + 1 brief por email + 2 entidades/alertas).

## 3.1 Onboarding corto

Preguntar solo: país, departamento/ciudad, categorías de interés, temas/entidades a
seguir, frecuencia, canal preferido.

Categorías iniciales: Política, Economía, Tecnología, Seguridad, Salud, Educación,
Medioambiente, Negocios, Deportes, Internacional relevante para Bolivia.

Implementación: nueva página en `frontend/src/pages/` (ej. `OnboardingPage.tsx`,
al lado de la ya existente `SubscribePage.tsx`), y columnas nuevas en `subscribers`
o una tabla `subscriber_categories` si es many-to-many.

## 3.2 Seguir entidades

Nuevo concepto de dominio — no existe en el repo:

```sql
CREATE TABLE entities (
  id BIGSERIAL PRIMARY KEY,
  canonical_name VARCHAR(200) NOT NULL,
  entity_type VARCHAR(30) NOT NULL,   -- person, organization, company, government_agency,
                                        -- location, law, industry, event
  country VARCHAR(10) NOT NULL DEFAULT 'BO',
  aliases TEXT[] NULL
);

CREATE TABLE subscriber_entity_follows (
  subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
  entity_id BIGINT NOT NULL REFERENCES entities(id),
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  PRIMARY KEY (subscriber_id, entity_id)
);
```

Requiere extracción de entidades (NER) sobre artículos/historias — se puede resolver
inicialmente con el mismo LLM ya usado (`src/llm/`) en un paso de post-procesamiento,
sin modelo propio (ver [no-construir-ahora.md](no-construir-ahora.md): no construir IA
propia).

## 3.3 Brief diario (5–10 historias, no 50)

Estructura por historia: lo más importante, por qué importa, qué cambió, fuentes.
Secciones: temas elegidos por el usuario, historias en seguimiento. Esto reemplaza el
envío actual (que probablemente manda todo lo recolectado) por una selección rankeada
y filtrada por preferencias — reusa `ranker.py` pero con un filtro de personalización
antes del corte a 5-10.

## 3.4 Canales de distribución (orden recomendado)

Web → **Email** (ya implementado, priorizar aquí porque genera recurrencia sin
depender de que el usuario recuerde visitar la web) → notificaciones web → WhatsApp/
Telegram (ya implementados, evaluar costo/reglas de Meta y Telegram antes de escalar
volumen) → audio brief → app móvil (mucho después, ver
[no-construir-ahora.md](no-construir-ahora.md)).

## 3.5 Feedback ligero

Por historia: Relevante / No me interesa / Ya conocía esto / Quiero seguir esta
historia / El resumen tiene un error. Alimenta directamente `analytics_events`
(Fase 0) y debería ajustar el ranking personal con el tiempo (empezar simple: boost/
penalización por categoría, no un modelo de recomendación complejo todavía).

## 3.6 Guardados y seguimiento

Guardar historia, seguir actualizaciones, compartir enlace, crear colección, recibir
alerta ante cambio importante. Tabla `saved_stories` (subscriber_id, story_id,
created_at) es suficiente para empezar.

## Criterio de salida

- ≥30% de usuarios nuevos completa el onboarding.
- Los usuarios abren briefs varias veces por semana.
- Se puede calcular retención D7 y D30 (depende de Fase 0).
- Existe un grupo de usuarios que se vería afectado si EcoBrief desapareciera.
