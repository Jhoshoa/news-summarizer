# AI Battle — Josoe Ichuta

---

## Ficha de Batalla

| Campo | Valor |
|---|---|
| **Nombre** | Josoe |
| **Alias** | The Scraper |
| **Rol** | Digital Waste Reduction Lead |
| **AI Weapon** | Zero-Waste Pipeline |
| **Signature Move** | El pipeline filtra, deduplica, clasifica y rankea antes de tocar un LLM. El 80% de los artículos scrapeados nunca llegan al modelo. |
| **Favorite Battle Song** | Tiësto — *Silence* |

---

## Proyecto: EcoBrief Bolivia

Plataforma que recolecta noticias de medios bolivianos (Radio Fides, Unitel, Red Uno, Red Bolivisión + NewsAPI), extrae el contenido útil, aplica 8 capas de deduplicación, clasifica por categoría, rankea por relevancia local, selecciona candidatos diversos, y **recién ahí** envía al LLM a resumir. Los briefs se distribuyen por WhatsApp, Telegram o Email según preferencias del suscriptor.

Stack: Python 3.11+ / FastAPI / PostgreSQL async / Groq (Llama 3.3 70B) / APScheduler / Twilio / Telegram Bot / Playwright.

---

## Presentación STAR — 10 minutos / 4 demos en vivo

---

### Demo 1: El problema en vivo (2 min)

**S** — Abro 4 pestañas de medios bolivianos. La misma noticia del tipo de cambio aparece en 3 sitios con titulares distintos y URLs diferentes. El usuario pierde tiempo, datos y atención.

**T** — Mostrar que el problema existe ahora, en Bolivia.

**A** — Navegación rápida: Radio Fides, Unitel, Red Uno. Todos cubriendo lo mismo. Luego abro EcoBrief.

**R** — El Home de EcoBrief ya muestra esa noticia **una sola vez**, resumida, con fuente original linkeada. Primer contraste.

> 🕐 0:00–2:00

---

### Demo 2: El Zero-Waste Pipeline en acción (3 min)

**S** — La mayoría de proyectos lanzan todo contra un LLM: caro, lento, derrochador.

**T** — Diseñar un pipeline donde la IA sea el último paso. Que el 80% de los artículos ni llegue al modelo.

**A** — Ejecuto `POST /trigger/summary` con `refresh=true`. El pipeline corre:

1. **NewsScraper** + **NewsAPICollector** → 47 artículos crudos
2. **Quality Gate** (`_filter_usable_articles`) → 32 útiles (descarta 15 sin cuerpo)
3. **Deduplicator** (`Deduplicator`) → 18 únicas (URL hash + fuzzy title ≥ 0.85)
4. **NewsClassifier** (`classifier.py`) → categoriza cada una
5. **NewsRanker** (`ranker.py`) → score 0–100 (recencia 15%, fuente 10%, calidad 17%, impacto 20%, relevancia Bolivia 20%, corroboración 10%, confianza 8%)
6. **Candidate selection** (`_select_summary_candidates`) → 12 candidatos (top por categoría, máx 2 por fuente)
7. **AIStoryDeduplicator** (`story_deduplicator.py`) → elimina redundancia semántica vía LLM
8. **NewsSummarizer** (`summarizer.py`) → **recién acá** toca el LLM (Groq Llama 3.3 70B)

**R** — 47 → 12 briefs. Tasa de reducción: ~74%. El LLM solo procesó el 26%. Muestro el log real.

> 🕐 2:00–5:00

---

### Demo 3: Impacto medible — el dashboard (2 min)

**S** — "Ahorramos recursos" necesita evidencia.

**T** — Mostrar métricas concretas del pipeline.

**A** — Abro `GET /api/impact-metrics`. El payload devuelve:

```json
{
  "collected_articles": 47,
  "duplicate_articles": 14,
  "summaries": 12,
  "reduction_rate": 0.7447,
  "estimated_pages_avoided": 35,
  "estimated_minutes_saved": 17.5,
  "estimated_data_saved_mb": 28.0,
  "ai_calls_avoided_estimated": 14,
  "pipeline": [
    {"label": "Recolectadas", "value": 47},
    {"label": "Utiles", "value": 32},
    {"label": "Unicas", "value": 18},
    {"label": "Candidatas", "value": 12},
    {"label": "Briefs", "value": 12}
  ]
}
```

Fórmulas: `paginas_evitadas = recolectadas - briefs`, `minutos = paginas * 0.5`, `MB = paginas * 0.8`.

**R** — El jurado ve el número en pantalla. 74% de reducción. 17.5 minutos ahorrados. 28 MB no descargados. Sin estimaciones vagas.

> 🕐 5:00–7:00

---

### Demo 4: Distribución omnicanal (2 min)

**S** — De nada sirve resumir si los briefs no llegan al usuario.

**T** — Entregar en el canal que el usuario elija, cuando lo elija.

**A** — Muestro `GET /api/preferences/preview`. Un suscriptor configuró:

- Canal: Telegram
- Categorías: economía, política
- Frecuencia: diario
- Horario: mañana

El scheduler (`APScheduler`) dispara `deliver_cached_summaries("morning")`. El `TelegramHandler` envía el mensaje con Markdown. El suscriptor recibe 3 briefs en vez de 20 artículos.

Muestro el mensaje real en Telegram: titulares, resúmenes, dato curioso y enlace a fuente.

**R** — 3 briefs. Sin ruido. Sin spam. En su canal preferido. A la hora que pidió.

> 🕐 7:00–9:00

---

### Cierre (1 min)

El proyecto no es "IA por IA". Es un **Zero-Waste Pipeline** que:

- Recolecta de fuentes reales bolivianas
- Filtra basura antes de procesar
- Deduplica en 8 capas (URL, título fuzzy, fingerprint SHA-256, histórico, semántico LLM, cluster, storage, delivery)
- Clasifica y rankea con reglas determinísticas
- **Solo entonces** toca un LLM
- Entrega briefs donde el usuario quiere, cuando quiere

> *"El pipeline filtra, deduplica, clasifica y rankea antes de tocar un LLM. El 80% de los artículos scrapeados nunca llegan al modelo."*

**Josoe** — *The Scraper* — Tiësto: *Silence*

---

## Referencias de código

| Componente | Archivo | Línea clave |
|---|---|---|
| Pipeline principal | `src/main.py` | `send_summaries()` L124 |
| Quality gate | `src/main.py` | `_filter_usable_articles()` L600 |
| Deduplicator | `src/processors/deduplicator.py` | `deduplicate()` L16 |
| Story fingerprint | `src/processors/story_fingerprint.py` | `build_content_fingerprint()` L49 |
| Classifier | `src/processors/classifier.py` | `classify_batch_async()` |
| Ranker | `src/processors/ranker.py` | `rank()` |
| AI story dedup | `src/processors/story_deduplicator.py` | `deduplicate()` |
| Summarizer | `src/processors/summarizer.py` | `summarize()` |
| Rewriter | `src/processors/rewriter.py` | `rewrite()` |
| Impact metrics | `src/db/repository.py` | `get_impact_metrics()` L482 |
| Distributors | `src/distributors/` | WhatsApp, Telegram, Email |
| Scheduler | `src/scheduler/cron.py` | `NewsScheduler` |
