# EcoBrief Bolivia

## Anexo tecnico

**Equipo:** Josoe Ichuta, Ingenieria; Raquel Auza, Digital-Academy  
**Proposito del anexo:** respaldar tecnicamente la propuesta ejecutiva para el concurso Green Tech.

---

## 1. Arquitectura general

EcoBrief Bolivia esta construido como una aplicacion web con backend FastAPI, frontend React/Vite y base de datos PostgreSQL.

Componentes:

- **Frontend:** interfaz de usuario para Home, Noticias, Detalle, Impacto y Suscripcion.
- **Backend API:** endpoints REST para articulos, resumenes, preferencias, impacto y triggers.
- **Collectors:** scraping de medios locales y fuentes externas.
- **Processors:** deduplicacion, clasificacion, ranking, resumen y reescritura.
- **LLM client:** integracion con proveedor IA.
- **Database:** persistencia de articulos, summaries, fuentes, categorias, suscriptores y corridas.
- **Distributors:** preparacion para WhatsApp y Telegram.
- **Scheduler:** ejecucion automatizada.

Alcance de confianza informativa:

- EcoBrief conserva enlace a la fuente original.
- Prioriza articulos con cuerpo, fecha y fuente identificada.
- Reduce dependencia de informacion obtenida por scroll en redes sociales.
- No reemplaza fact-checking periodistico, pero ayuda a evitar contenido no trazable.

**Diagrama:** `diagrams/technical-architecture.puml`.

---

## 2. Pipeline de procesamiento

Flujo principal:

1. Se inicia una corrida manual o programada.
2. El sistema intenta reutilizar summaries recientes si no se solicita refresh.
3. Si no hay cache util, recolecta noticias nuevas.
4. Filtra articulos sin contenido suficiente.
5. Deduplica dentro del lote.
6. Clasifica por categoria.
7. Rankea por relevancia.
8. Persiste articulos.
9. Calcula fingerprints y detecta duplicados historicos.
10. Selecciona candidatos unicos para resumen.
11. Genera summaries con IA.
12. Reescribe o normaliza summaries.
13. Deduplica summaries.
14. Guarda resultados.
15. Calcula metricas.
16. Prepara envio segun suscriptores.

**Diagrama:** `diagrams/technical-pipeline.puml`.

---

## 3. Modelo de datos relevante

### 3.1 Articulos

Tabla principal: `news_articles`

Campos relevantes:

- `title`
- `url`
- `url_hash`
- `description`
- `content`
- `image_url`
- `source_id`
- `category_id`
- `published_at`
- `raw_payload`
- `score`
- `canonical_key`
- `content_fingerprint`
- `story_cluster_id`
- `duplicate_of_article_id`
- `duplicate_reason`
- `similarity_score`

### 3.2 Summaries

Tabla principal: `news_summaries`

Campos relevantes:

- `article_id`
- `category_id`
- `title`
- `summary`
- `fact`
- `llm_provider`
- `llm_model`
- `summary_date`
- `story_cluster_id`
- `source_article_count`

### 3.3 Corridas del pipeline

Tabla: `collection_runs`

Campos de trazabilidad:

- `raw_collected_count`
- `usable_count`
- `quality_dropped_count`
- `deduplicated_count`
- `duplicate_dropped_count`
- `ranked_count`
- `summary_candidates_count`
- `summaries_count`
- `used_cached_articles`
- `used_cached_summaries`
- `metrics_payload`

---

## 4. Deduplicacion

EcoBrief usa varios niveles de deduplicacion.

### 4.1 Dedupe por URL

Cada URL se convierte en hash. Esto evita guardar o procesar el mismo enlace repetido.

### 4.2 Dedupe por titulo

Dentro de una corrida, se comparan titulos normalizados para detectar articulos muy similares.

### 4.3 Dedupe historico por historia

Sprint 6 agrega deduplicacion historica.

Se calcula:

```text
canonical_key = categoria + titulo_normalizado + fragmento_contenido_normalizado
content_fingerprint = sha256(canonical_key)
```

Esto permite agrupar noticias equivalentes aunque tengan URLs distintas.

Campos usados:

- `canonical_key`: clave legible normalizada.
- `content_fingerprint`: hash estable.
- `story_cluster_id`: grupo de historia.
- `duplicate_of_article_id`: articulo canonico.
- `duplicate_reason`: motivo.
- `similarity_score`: puntaje de similitud.

Comportamiento:

- El duplicado no se borra.
- Se conserva para auditoria.
- Se marca como duplicado.
- Se excluye de candidatos a resumen.

---

## 5. Ranking

El ranking prioriza noticias segun:

- Recencia.
- Fuente.
- Calidad del contenido.
- Impacto nacional.
- Relevancia para Bolivia.
- Corroboracion multi-fuente.
- Confianza de categoria.
- Penalizaciones por contenido pobre o duplicado.

El objetivo es no resumir todo, sino resumir lo mas relevante.

---

## 6. IA y eficiencia

La IA se usa en dos momentos principales:

- Clasificacion cuando corresponde.
- Resumen y reescritura de summaries.

Practicas de eficiencia:

- Filtrar antes de IA.
- Deduplicar antes de IA.
- Rankear antes de IA.
- Limitar candidatos.
- Cachear summaries.
- Evitar summaries repetidos.

Esto reduce tokens, llamadas y costo.

---

## 7. APIs principales

Endpoints relevantes:

```text
GET  /api/articles
GET  /api/articles/{id}
GET  /api/articles/{id}/related
GET  /api/summaries
GET  /api/impact-metrics
POST /trigger/summary
GET  /api/preferences/preview
POST /api/preferences
```

---

## 8. Frontend

Vistas principales:

- **Home:** noticias destacadas, resumen visual e indicadores.
- **Noticias:** listado de articulos y summaries.
- **Detalle:** articulo original, fuente, resumen IA si existe y cuerpo.
- **Impacto:** metricas Green Tech.
- **Suscripcion:** preferencias de categoria, frecuencia y canal.

---

## 9. Metricas

Metricas reales:

- Recolectadas.
- Utiles.
- Unicas.
- Duplicadas.
- Rankeadas.
- Candidatas a IA.
- Briefs.
- Cache.

Metricas estimadas:

- Paginas evitadas.
- Minutos ahorrados.
- MB evitados.
- Tasa de reduccion.
- Llamadas IA evitadas.
- Sesiones de busqueda o scroll evitadas.

Nota metodologica:

> Las metricas ambientales son estimaciones operativas basadas en reduccion de paginas, articulos y llamadas IA. No representan una medicion energetica directa.

---

## 10. Costos tecnicos y despliegue

### 10.1 Infraestructura elegida

Para un primer despliegue, EcoBrief puede operar en una arquitectura simple de bajo costo:

| Componente | Decision tecnica | Motivo |
|---|---|---|
| Servidor | Hostinger KVM 2 por 1 ano | Suficiente para backend, frontend, BD y cron-jobs |
| Base de datos | PostgreSQL en el mismo VPS | Reduce costos y complejidad inicial |
| Backend | FastAPI en el VPS | Control total del pipeline |
| Frontend | Build React/Vite servido desde el VPS | No requiere hosting separado |
| Cron-jobs | Scheduler/cron en el VPS | No requiere servicio externo |
| Dominio | NIC Bolivia | Identidad local `.bo` |

Costo base:

```text
Hostinger KVM 2: USD 8.99/mes referencial
Hostinger KVM 2 anual: USD 107.88 referencial
Dominio NIC Bolivia: 55 Bs/ano
```

Los valores pueden variar por promocion, impuestos, plazo contratado y tipo de cambio.

### 10.2 Mensajeria

| Canal | Proveedor | Costo | Uso recomendado |
|---|---|---:|---|
| Email / SMTP | Gmail SMTP con Google App Password | Gratuito dentro de los limites de envio de Google; luego migrable a Brevo u otro SMTP | Validaciones, avisos y briefs por correo |
| Telegram | Bot API | Gratuito | Canal principal de bajo costo para briefs |
| WhatsApp | Twilio WhatsApp Business | Variable; Bolivia referencial USD 0.0116 outbound/minuto segun tabla Twilio | Piloto o canal premium |

Recomendacion: iniciar con Telegram y Gmail SMTP con App Password para mantener costos bajos. WhatsApp debe activarse cuando exista presupuesto o patrocinio para mensajeria. Si el volumen de correo crece, se debe migrar a Brevo, Amazon SES u otro proveedor SMTP transaccional.

### 10.3 IA actual

Proveedor actual: Groq.

Modelos configurados:

| Tarea | Modelo |
|---|---|
| Resumen de calidad | `llama-3.3-70b-versatile` |
| Tareas rapidas | `llama-3.1-8b-instant` |
| Balanceado / reescritura | `llama-3.1-70b-versatile` |

Precios Groq referenciales:

| Modelo | Input / 1M tokens | Output / 1M tokens |
|---|---:|---:|
| Llama 3.3 70B Versatile | USD 0.59 | USD 0.79 |
| Llama 3.1 8B Instant | USD 0.05 | USD 0.08 |

### 10.4 Alternativas IA

| Proveedor | Modelo referencial | Input / 1M tokens | Output / 1M tokens | Uso sugerido |
|---|---|---:|---:|---|
| Groq | Llama 3.3 70B Versatile | USD 0.59 | USD 0.79 | Opcion actual |
| DeepSeek | V4 Flash | USD 0.14 cache miss; USD 0.0028 cache hit | USD 0.28 | Alternativa economica |
| DeepSeek | V4 Pro | USD 0.435 cache miss; USD 0.003625 cache hit | USD 0.87 | Alternativa con mayor capacidad |
| Anthropic | Claude Haiku 4.5 | USD 1.00 | USD 5.00 | Opcion Claude de menor costo |
| Anthropic | Claude Sonnet 4.6 | USD 3.00 | USD 15.00 | Mayor calidad, mayor costo |
| OpenAI | GPT-5.4 mini | USD 0.75 | USD 4.50 | Alternativa economica dentro de OpenAI |
| OpenAI | GPT-5.4 | USD 2.50 | USD 15.00 | Mayor capacidad, mayor costo |

### 10.5 Control tecnico de costos

El sistema reduce costos operativos porque:

- Filtra articulos sin contenido antes de IA.
- Deduplica antes de IA.
- Rankea antes de IA.
- Limita candidatos por categoria.
- Cachea summaries.
- Evita summaries duplicados.
- Permite usar modelos pequenos para tareas simples.

Formula:

```text
costo_ia = llamadas_ia * costo_promedio_por_llamada
ahorro_ia = llamadas_evitas * costo_promedio_por_llamada
```

### 10.6 Fuentes de referencia

- Hostinger VPS: https://www.hostinger.com/vps-hosting
- NIC Bolivia: costo indicado por el equipo, 55 Bs/ano.
- Google App Passwords: https://support.google.com/accounts/answer/185833
- Limites de envio Gmail/Google Workspace: https://support.google.com/a/answer/166852
- Twilio WhatsApp pricing: https://www.twilio.com/en-us/whatsapp/pricing
- Groq pricing: https://groq.com/pricing/
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
- Anthropic Claude pricing: https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI pricing: https://openai.com/api/pricing/

---

## 11. Seguridad y configuracion

Buenas practicas:

- Variables sensibles en `.env`.
- No commitear claves reales.
- Configuracion por entorno.
- Base de datos PostgreSQL.
- Fuentes configurables en YAML.
- Tests para cambios en scraping.

---

## 12. Testing

El proyecto incluye tests para:

- Clasificacion.
- Ranking.
- Scraping.
- Extraccion de body.
- Deduplicacion historica.
- Summaries.
- Preferencias.
- API OpenAPI.
- Metricas de impacto.

Comandos:

```bash
pytest
ruff check src tests
```

---

## 13. Riesgos tecnicos

| Riesgo | Mitigacion |
|---|---|
| Cambios de HTML en fuentes | Tests por fuente y selectores configurables |
| Falsos positivos en dedupe | Umbral conservador y marcado sin borrado |
| Falsos negativos | Ajuste de reglas, entidades y comparacion multi-fuente |
| Costos IA | Dedupe, cache, ranking y limites |
| Mensajeria productiva | Activacion gradual |
| Metricas ambientales estimadas | Transparencia metodologica |
| Informacion falsa o descontextualizada | Trazabilidad a fuente original y priorizacion de contenido verificable |

---

## 14. Roadmap tecnico

### Corto plazo

- Backfill de fingerprints historicos.
- Exponer metricas historicas de duplicados.
- Mostrar fuentes relacionadas en UI.
- Alertas de errores de scraping.
- Medir reduccion estimada de busquedas repetitivas en redes sociales.

### Mediano plazo

- Medicion real de bytes descargados.
- Dashboard historico.
- WhatsApp/Telegram productivo.
- Monitoreo de costos IA.
- Integracion de boletines y comunicados de instituciones del Estado.

### Largo plazo

- Deteccion por entidades.
- Evaluacion de precision de dedupe.
- Planes de suscripcion para usuarios avanzados, organizaciones y analistas.
- Panel institucional para monitoreo de noticias, comunicados y alertas publicas.

---

## 15. Conclusion tecnica

EcoBrief Bolivia es un MVP funcional con arquitectura modular y trazabilidad suficiente para demostrar valor Green Tech. Su fortaleza tecnica esta en reducir el volumen antes de usar IA, conservar metricas del pipeline y transformar noticias dispersas en briefs medibles.
