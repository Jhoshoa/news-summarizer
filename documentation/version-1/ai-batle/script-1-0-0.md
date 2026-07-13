# Script de Presentación — EcoBrief Bolivia
## AI Battle — Josoe Ichuta (STAR Method · 10 min)

---

## Ficha

| Campo | Valor |
|---|---|
| **Nombre** | Josoe |
| **Alias** | The Scraper |
| **Rol** | Digital Waste Reduction Lead |
| **AI Weapon** | Zero-Waste Pipeline |
| **Signature Move** | El pipeline filtra, deduplica, clasifica y rankea antes de tocar un LLM. El 80% de los artículos scrapeados nunca llegan al modelo. |
| **Song** | Tiësto — *Silence* |

---

## ⏱ Estructura: 10 min

| Bloque | Técnica | Tiempo |
|---|---|---|
| 1. Problema | **S**ituation | 1.5 min |
| 2. Tareas | **T**ask | 1.5 min |
| 3. Acción: Pipeline sin IA | **A**ction (parte 1) | 2.5 min |
| 4. Acción: Selección + IA | **A**ction (parte 2) | 2.5 min |
| 5. Resultado + demo | **R**esult | 1.5 min |
| 6. Cierre | Signature | 0.5 min |

---

## 1. SITUATION — El problema (1.5 min)

Hola buenas tardes a todos.

Les presento **EcoBrief Bolivia**: un proyecto que resume con IA las noticias más relevantes del día.

**El problema:** Muchos de nosotros queremos estar informados — política, economía, deportes, entretenimiento — pero ¿cómo lo hacemos?

- Vemos TV, noticieros, sección de deportes
- Escuchamos radio
- O — lo más común hoy — scroleamos redes sociales sin parar

En resumen: **invertimos mucho tiempo** para estar informados.

Y además, una misma noticia aparece en 3, 4 o 5 medios distintos con titulares diferentes. Estamos consumiendo datos duplicados, páginas enteras con publicidad, y procesando información que no aporta nada nuevo.

> *¿Cómo podemos reducir ese tiempo, ese consumo de datos, y aún así seguir informados?*

---

## 2. TASK — Las 4 tareas (1.5 min)

Para resolver esto, necesitábamos 4 cosas:

1. **Web scraper** que vaya a fuentes conocidas (Radio Fides, Unitel, Red Uno, Red Bolivisión + NewsAPI) y obtenga las noticias del día
2. **Pipeline de filtrado** que limpie, deduplique, clasifique y rankee — **sin IA**
3. **Interfaz** que presente las noticias más relevantes al usuario
4. **Scheduler** que ejecute el pipeline varias veces al día (08:00, 10:00, 13:00, 17:00)

Tarea clave: **que la IA sea el último paso, no el primero.** La lógica de negocio — qué es duplicado, qué es relevante para Bolivia — debía resolverse con código determinístico, no con un LLM.

---

## 3. ACTION — Pipeline sin IA (2.5 min)

Allá por 2023, empecé creando el scraper. Usando `httpx` + `BeautifulSoup` + `lxml`, cada fuente definida en `config/sources.yaml` con selectores CSS. Cuando el HTML cambia — y cambia seguido — hay un fallback genérico que extrae todos los enlaces y filtra los que parecen artículos periodísticos.

Las noticias recolectadas pasan por este **Zero-Waste Pipeline**:

```
  Recolectadas (47)
       │
  ┌────▼──────────────┐
  │ Quality Gate      │  → descarta artículos sin cuerpo, sin fecha,
  │ (determinístico)  │     o que solo repiten el título
  └────┬──────────────┘
       │ (32 útiles, 15 descartadas)
       │
  ┌────▼──────────────┐
  │ Deduplicator      │  → 1. URL hash (MD5)
  │ (8 capas, pero    │  → 2. Fuzzy title (SequenceMatcher ≥ 0.85)
  │  acá van 2)       │     Se queda con la más reciente
  └────┬──────────────┘
       │ (18 únicas)
       │
  ┌────▼──────────────┐
  │ NewsClassifier    │  → 5 categorías: economía, política, deportes,
  │ (reglas x peso)   │     tecnología, entretenimiento
  │                    │  → Pesos: title×3, description×2, content×1,
  └────┬──────────────┘     source_category×2.5
       │               → Si la confianza es baja (< 0.62), usa IA como fallback
       │
  ┌────▼──────────────┐
  │ NewsRanker        │  → Score 0-100 con 7 factores:
  │ (7 factores)      │     recencia 15%, fuente 10%, calidad 17%,
  │                    │     impacto 20%, relevancia Bolivia 20%,
  └────┬──────────────┘     corroboración 10%, confianza categoría 8%
       │               → Penalizaciones por: texto corto, sin fecha,
       │                 fuente desconocida, sin contexto boliviano
```

**Hasta acá: 0 llamadas a la IA.** Todo es Python puro con librerías estándar.

---

## 4. ACTION — Selección + IA (2.5 min)

Una vez rankeadas, seleccionamos los **mejores candidatos por categoría**:

| Categoría | Límite |
|---|---|
| Deportes | 5 |
| Entretenimiento | 5 |
| Tecnología | 5 |
| Política | 8 |
| Economía | 8 |

Con diversidad: máximo **2 artículos por fuente**.

**Antes de tocar el LLM**, hacemos 3 filtros más:

1. **AI Story Dedup** — Mandamos los candidatos a un modelo `llama-3.1-8b-instant` con un prompt en español que detecta si dos textos cubren el MISMO hecho noticioso. Si son redundantes, nos quedamos con el de mayor score. El prompt tiene criterios muy precisos para evitar falsos positivos (instrucciones como "prioriza falsos negativos sobre falsos positivos").
2. **Filtro contra DB** — Como el pipeline corre varias veces al día, verificamos si ya existe un resumen de ese artículo. Si ya se resumió, lo quitamos.
3. **Story fingerprint** — Calculamos un SHA-256 de `categoría + título normalizado + excerpt`. Si coincide con uno guardado en los últimos 3 días, es duplicado histórico.

**Recién ahora** mandamos al LLM a resumir. Usamos `llama-3.3-70b-versatile` con temperatura 0.3 para obtener resúmenes consistentes de 180-320 caracteres más un "dato" clave.

**LLM Router:** Por defecto usamos **Groq** (tiers gratuitos). Pero Groq tiene rate limits. Cuando devuelve 429, el router cambia automáticamente a **OpenAI** (`gpt-4o-mini`). Si OpenAI también rate-limitea, salta a **NVIDIA** (`mistral-small`). Los rate limits se reinician cada día, y al inicio de cada pipeline siempre arrancamos por Groq. He monitoreado la base de datos y efectivamente los tres se usan.

Después de resumir, un **NewsRewriter** normaliza el estilo (voz profesional, tercera persona, español neutral) usando el modelo fast.

Y finalmente guardamos en PostgreSQL con metadatos del proveedor y modelo usado.

---

## 5. RESULT — Resultado + demo (1.5 min)

El sistema está desplegado en un VPS de Hostinger. El frontend en React + Vite consume la API de FastAPI.

**¿Qué tenemos?**

- **Home** con noticias resumidas y al costado las recolectadas con fuente, imagen y fecha
- **Página de datos** — indicadores económicos (BCB + Binance USDT/BOB) y clima de 9 ciudades bolivianas (Open-Meteo)
- **Página de impacto** — métricas globales y por corrida:

```
Ejemplo real — 15 de junio 2026:
  Recolectadas: 174 → Útiles: 173 → Únicas: 169 → Briefs: 39
  Tasa de reducción: 77.6%
  Páginas evitadas: 135
  Minutos ahorrados: 67.5
```

- **Suscripción** — el usuario elige categorías, frecuencia (diario/días hábiles/semanal), horario (mañana/tarde/noche) y canal

**Canales de distribución:**

| Canal | Estado |
|---|---|
| **Email** | ✅ Funcional con Gmail App Password (desactivado porque usa mi correo personal) |
| **Telegram** | 🚧 Bot funcional, en integración con el scheduler |
| **WhatsApp** | ⏸ Twilio configurado, desactivado por costos por mensaje |

*Para futuro: comprar suscripción SMTP, activar Telegram en producción, evaluar costo de Twilio.*

---

## 6. CIERRE (0.5 min)

> El pipeline filtra, deduplica, clasifica y rankea antes de tocar un LLM. El 80% de los artículos scrapeados nunca llegan al modelo.

**Josoe** — *The Scraper* — Tiësto: *Silence*

---

## Bonus: Telegram con STAR

Si te sirve para la sección de preguntas o mejora futura:

**S** — Los usuarios de Telegram no reciben briefs porque el bot está implementado pero no integrado con el scheduler de entregas.

**T** — Activar la entrega automática de briefs por Telegram respetando preferencias, frecuencia y horario.

**A** — El `TelegramHandler` ya existe en `src/distributors/telegram_handler.py` con:
- Comandos `/start`, `/preferencias`, `/cancelar`, `/ayuda`
- Inline keyboard para selección de categorías
- `send_message()` con parse_mode Markdown
- Suscripción guardada en DB vía `db.save_subscription(telegram_id=chat_id, channel="telegram")`

Lo que falta: en `main.py` el delivery ya itera suscriptores con `sub.channel == "telegram"` y llama a `telegram.send_message()`. El `telegram.app` debe inicializarse con `Application.builder().token().build()` en el startup.

**Mejora sugerida:**

```python
# En src/main.py, dentro de startup():
self.telegram.app = Application.builder().token(
    self.settings.telegram_bot_token
).build()
```

Y en `send_message()`, en vez de `self.app.bot.send_message()`, usar `self.app.bot.send_message()` que ya está implementado. Con eso y el token configurado en `.env`, los briefs llegarán automáticamente.

**R** — Usuarios de Telegram reciben briefs sin intervención manual. Sin costo por mensaje. Sin límite de suscriptores.

---

## Referencias de código

| Componente | Archivo | Línea |
|---|---|---|
| Pipeline principal | `src/main.py` | `send_summaries()` L124 |
| Quality gate | `src/main.py` | `_filter_usable_articles()` L600 |
| Deduplicator | `src/processors/deduplicator.py` | `deduplicate()` L16 |
| Story fingerprint | `src/processors/story_fingerprint.py` | `build_content_fingerprint()` L49 |
| Classifier | `src/processors/classifier.py` | `classify_batch_async()` |
| Ranker | `src/processors/ranker.py` | `rank()` |
| AI story dedup | `src/processors/story_deduplicator.py` | `deduplicate()` L21 |
| Summarizer | `src/processors/summarizer.py` | `summarize()` |
| Rewriter | `src/processors/rewriter.py` | `rewrite()` |
| LLM Router | `src/llm/router.py` | `chat()` |
| Impact metrics | `src/db/repository.py` | `get_impact_metrics()` L482 |
| Telegram handler | `src/distributors/telegram_handler.py` | `send_message()` L154 |
| Scheduler | `src/scheduler/cron.py` | `NewsScheduler` |
