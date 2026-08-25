# Fase 3 — Personalización que genere recurrencia

**Estado actual (revisado ago-2026):** más avanzado de lo que este documento decía —
`SubscribePage.tsx` + `/api/preferences/*` ya cubren canal, categorías, frecuencia, hora
preferida, consentimiento, preview y baja, con validación en frontend y backend. El envío
diario (`_deliver_summaries` en `main.py`) **ya filtra por las categorías del suscriptor**
y **ya limita a 10 historias**, no manda todo el catálogo — eso es 3.1 y 3.3 en la
práctica, aunque nadie los haya llamado así. Los canales de distribución (Email/WhatsApp/
Telegram) tenían bugs reales que impedían el envío/recepción confiable — arreglados
(ver `fbe50ac`/`e48d486`). Lo que sigue faltando de verdad: onboarding con ubicación,
seguimiento de entidades (3.2), y guardados persistentes (3.6, hoy solo un evento de
analítica vía 3.5, no una tabla).

**Tiempo estimado restante:** bajo — la mayor parte del esfuerzo original ya está hecho.

## 3.1 Onboarding corto — parcialmente implementado

Canal, categorías, frecuencia y hora preferida ya se preguntan en `/suscribirse`. Lo que
pide el roadmap original y falta: país/departamento/ciudad, y temas/entidades a seguir.

**País/departamento/ciudad — deliberadamente no agregado todavía:** ningún artículo tiene
su departamento poblado de forma confiable hoy (`NewsArticle.department`/`Story.department`
existen en el esquema pero casi nunca se llenan), así que pedirle ubicación al usuario no
cambiaría nada de lo que recibe — sería fricción en el formulario sin beneficio real.
Vale la pena agregarlo cuando exista contenido que realmente varíe por región.

Temas/entidades a seguir — depende de 3.2 (NER), ver ahí.

No se construyó una `OnboardingPage.tsx` separada como sugería la versión original de este
documento: `SubscribePage.tsx` ya cumple ese rol razonablemente bien (incluye preview) y
duplicar el formulario habría sido mantener dos superficies para lo mismo sin necesidad.

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

## 3.3 Brief diario (5–10 historias, no 50) ✅ implementado

`_deliver_summaries` (`main.py`) ya filtra `summaries` por `sub.categories` antes de
armar el mensaje, y corta a `user_news[:10]`. Lo que falta de la visión original: una
sección aparte para "historias en seguimiento" (depende de 3.6) y mostrar explícitamente
"qué cambió" por historia — eso ya existe a nivel de dato (`Story.last_update_note`,
Fase 1.4) pero no se incluye todavía en el texto del brief que se envía por canal.

## 3.4 (parte) "Qué cambió" en el brief ✅ implementado

Cierra el ciclo de Fase 1.4: `Story.last_update_note` ya existía pero nada lo mostraba
fuera de `GET /api/stories/{id}`. `Database.get_story_update_notes` (consulta batch,
una sola vez por lote de entrega, no una por suscriptor) + `NewsSummarizerApp
._attach_story_update_notes` enriquecen cada summary con `update_note` antes del loop de
envío; `_format_summary` (WhatsApp/Telegram) y `_format_email_summary` (texto plano +
HTML) lo incluyen cuando existe. Degrada con gracia: si la consulta falla, el brief se
manda igual, sin esa línea.

**Verificado:** 9 tests nuevos, y contra el Postgres real (con commit + limpieza
posterior): una historia real recibió una nota temporal, `get_story_update_notes` la
trajo correctamente (y no trajo la de una historia sin nota), y el pipeline completo
(`_attach_story_update_notes` → `_format_summary`/`_format_email_summary`) la incluyó
en el mensaje de WhatsApp/Telegram y en el email (texto y HTML).

## 3.4 (resto) Canales de distribución (orden recomendado)

Web → **Email** (ya implementado, priorizar aquí porque genera recurrencia sin
depender de que el usuario recuerde visitar la web) → notificaciones web → WhatsApp/
Telegram (ya implementados, evaluar costo/reglas de Meta y Telegram antes de escalar
volumen) → audio brief → app móvil (mucho después, ver
[no-construir-ahora.md](no-construir-ahora.md)).

## 3.5 Feedback ligero ✅ implementado

`StoryFeedback.tsx` (`frontend/src/components/news/`), montado en `ArticleDetailPage`
junto al resumen IA: tres reacciones mutuamente excluyentes (Relevante / No me interesa /
Ya lo sabía, vía `feedback_submitted` con `metadata.feedback_type`) más un botón
independiente "Seguir esta historia" (vía `story_saved`). "El resumen tiene un error" ya
existía desde Fase 2.5 (`StoryTrustPanel`, mismo evento `feedback_submitted` con
`feedback_type: 'error_report'`) — no se duplicó.

Cero cambios de backend: ambos tipos de evento (`feedback_submitted`, `story_saved`) ya
estaban en `ALLOWED_EVENT_NAMES` desde Fase 0.1. **Lo que falta de la visión original:**
usar estos eventos para ajustar el ranking personal (boost/penalización por categoría) —
hoy se registran en `analytics_events` pero nada los lee todavía para personalizar nada.
Vale la pena esperar a tener volumen real de reacciones antes de construir esa lógica.

**Verificado:** 19/19 tests de frontend (4 nuevos), `tsc`/`eslint` limpios, reconstruido
en Docker.

## 3.6 Guardados y seguimiento — parcialmente cubierto

"Seguir esta historia" ya dispara `story_saved` (3.5), pero solo como evento de
analítica — no hay tabla `saved_stories` ni una vista de "tus historias guardadas" donde
el usuario pueda volver a verlas. Construir la tabla real cuando el evento `story_saved`
muestre volumen de uso real que la justifique. Compartir enlace, colecciones y alertas
por cambio siguen sin construir.

## Criterio de salida

- ≥30% de usuarios nuevos completa el onboarding.
- Los usuarios abren briefs varias veces por semana.
- Se puede calcular retención D7 y D30 (depende de Fase 0).
- Existe un grupo de usuarios que se vería afectado si EcoBrief desapareciera.
