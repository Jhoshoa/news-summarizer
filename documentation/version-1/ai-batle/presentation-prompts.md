# Presentation Prompts - EcoBrief Bolivia
## Animacion profesional basada en `script-1-0-1.md`

Este documento contiene prompts por etapa para generar una presentacion animada profesional con herramientas como Nano Banana, Google Flow, Meta AI, Runway, Pika, Kling u otras plataformas de video/imagen IA.

La presentacion sigue el metodo **STAR**:

- **S**ituation: problema del desperdicio digital informativo.
- **T**ask: que habia que construir.
- **A**ction: arquitectura, pipeline y uso responsable de IA.
- **R**esult: MVP, metricas, demo y cierre.

Objetivo visual: una presentacion moderna para audiencia de desarrolladores, pero entendible para cualquier persona tecnica. Debe sentirse como un demo/pitch de producto, no como una clase con demasiados bullets.

---

## Estilo global para todos los videos

Usa este bloque como prefijo en todos los prompts si la plataforma permite prompts largos.

```text
Professional cinematic tech presentation, clean modern UI, Bolivia context, Green Tech theme, realistic but slightly stylized 3D/2.5D animation, dark neutral background with restrained green accents, no childish cartoon style, no exaggerated sci-fi, no clutter, no random text, no fake logos, no distorted hands, no unreadable UI text, no watermark. 

Main character: Bolivian software engineer / young professional, late 20s to mid 30s, casual smart clothing, focused but tired at first, later confident and calm. 

Visual identity: EcoBrief Bolivia, colors deep navy, neutral gray, white, and ecological green. 

Presentation mood: professional, clear, elegant, developer-friendly, product demo quality.

Camera style: smooth cinematic camera moves, shallow depth of field only when useful, crisp readable interface elements, clean typography, subtle motion graphics.
```

### Personaje recurrente

Mantener el mismo personaje durante toda la presentacion:

```text
A Bolivian male software engineer / product builder, late 20s to mid 30s, short dark hair, medium skin tone, wearing a dark green overshirt over a neutral t-shirt, smartwatch, working in a modern but realistic desk setup. He represents the user who wants to stay informed and later becomes the builder of EcoBrief Bolivia.
```

### Estilo de texto en pantalla

Cuando pidas texto, usa frases cortas. Las plataformas suelen fallar con mucho texto. Si el texto queda mal, genera el video sin texto y agrega texto despues en CapCut, Premiere, DaVinci o Canva.

Fuente sugerida para postproduccion:

- Titulos: Inter / Manrope / Sora Semibold.
- Texto secundario: Inter Regular.
- Colores: fondo `#0f172a`, verde `#16a34a`, gris `#374151`, blanco `#f8fafc`.

---

## Estructura recomendada

| Escena | STAR | Duracion | Funcion |
|---|---:|---:|---|
| 0 | Intro | 8-10s | Presentar EcoBrief |
| 1 | Situation | 20-25s | Mostrar el problema humano |
| 2 | Situation | 15-20s | Mostrar desperdicio digital |
| 3 | Task | 20-25s | Mostrar las 4 tareas |
| 4 | Action | 20-25s | Arquitectura general |
| 5 | Action | 30-35s | Pipeline antes de IA |
| 6 | Action | 25-30s | Uso responsable de IA |
| 7 | Result | 25-30s | MVP y demo de producto |
| 8 | Result | 20-25s | Metricas de impacto |
| 9 | Cierre | 10-15s | Mensaje final |

Duracion total estimada: 3.5 a 4.5 minutos de video visual. Puedes hablar encima usando el script completo de 8-10 minutos y dejar que los videos funcionen como apoyo visual.

---

# 0. INTRO - EcoBrief Bolivia

## Objetivo

Abrir con una imagen profesional del producto y el concepto: IA responsable para reducir ruido informativo.

## Prompt video

```text
Create a professional cinematic opening for a tech product presentation called "EcoBrief Bolivia". Start with a dark elegant digital map silhouette of Bolivia made of subtle news article fragments and data points. The fragments are noisy at first, then they compress into a clean green signal line and form a minimal dashboard preview with summarized news cards. 

Style: modern Green Tech, developer conference quality, deep navy background, ecological green accents, crisp UI, subtle motion graphics, no excessive sci-fi, no clutter. 

Camera: slow push-in, smooth, premium SaaS/product demo feeling. 

On-screen text, large and clean: "EcoBrief Bolivia"
Secondary text: "IA responsable para reducir el desperdicio digital informativo"

Duration: 8 seconds, 16:9, high resolution.
```

## Texto para postproduccion

```text
EcoBrief Bolivia
IA responsable para reducir el desperdicio digital informativo
```

## Voz sugerida

"Hola, buenas tardes a todos. Hoy les presento EcoBrief Bolivia, una plataforma que usa inteligencia artificial responsable para reducir el desperdicio digital informativo."

---

# 1. SITUATION - El usuario quiere estar informado

## Objetivo

Mostrar al personaje intentando informarse por medios tradicionales y digitales: TV, radio, sitios web y redes sociales.

## Prompt video

```text
Create a realistic cinematic scene of the recurring Bolivian young professional sitting at his desk in the evening, trying to stay informed. Around him, show multiple information sources: a TV news broadcast in the background, a radio/podcast waveform on a small speaker, several browser tabs with news websites on a laptop, and a phone with endless social media scrolling. 

The character looks focused at first, then overwhelmed. News headlines and notification cards multiply around him as floating UI panels, but keep them abstract and mostly unreadable, using only short generic words like "Politica", "Economia", "Deportes", "Ultima hora". 

Style: professional, realistic 2.5D motion, not cartoon, clean but slightly chaotic, Bolivia context, green and navy color accents. 

Camera: medium shot, slow orbit from left to right, subtle zoom into the character's tired face.

No logos, no real TV brands, no random readable long text.
Duration: 20 seconds, 16:9.
```

## Texto para postproduccion

```text
Queremos estar informados...
pero el flujo esta fragmentado.
```

## Voz sugerida

"El problema que vimos es simple: muchas personas queremos estar informadas sobre politica, economia, deportes, tecnologia y entretenimiento. Pero para lograrlo abrimos varios medios, vemos noticieros, escuchamos radio o scrolleamos redes sociales durante mucho tiempo."

---

# 2. SITUATION - Desperdicio digital informativo

## Objetivo

Visualizar el desperdicio: tiempo perdido, datos moviles, paginas repetidas, publicidad y noticias duplicadas.

## Prompt video

```text
Create a professional motion graphics scene explaining "digital information waste". Show the same news story duplicated across many browser windows and mobile cards. Each duplicate loads heavy page elements: ads, images, scripts, popups, and repeated headlines. The character scrolls and opens tabs, while a timer increases and a mobile data meter drains. 

Then the duplicated cards begin to stack into a heavy noisy pile labeled visually with simple icons: clock, mobile data, duplicate pages, low trust. Avoid too much text; use iconography and clean UI motion.

Style: sleek SaaS explainer, developer conference, dark navy background, green highlights only for useful signal, red/orange only subtly for waste. 

Camera: dynamic top-down view of windows multiplying, then smooth transition to a simplified waste dashboard.

On-screen short text only:
"Tiempo perdido"
"Datos consumidos"
"Noticias repetidas"
"Ruido digital"

Duration: 18 seconds, 16:9.
```

## Texto para postproduccion

```text
Tiempo perdido
Datos consumidos
Noticias repetidas
Ruido digital
```

## Voz sugerida

"Leemos la misma noticia repetida en distintos medios, cargamos paginas completas con publicidad, perdemos tiempo comparando titulares y consumimos informacion fragmentada."

## Transicion recomendada

Cerrar con una pregunta grande al centro:

```text
Como reducimos el ruido sin dejar de informarnos?
```

---

# 3. TASK - Las 4 piezas que habia que construir

## Objetivo

Esta escena si puede ser mas presentacion: bullets claros, animados uno por uno.

## Prompt video

```text
Create a clean animated technical slide for a developer audience. Dark navy background, subtle green grid lines, four professional cards appearing one by one with smooth motion. Each card has an icon and a short label.

Card 1: web scraper icon, label "Recolectar noticias"
Card 2: filter/funnel icon, label "Filtrar, deduplicar, clasificar y rankear"
Card 3: web dashboard icon, label "Presentar briefs relevantes"
Card 4: clock/cron icon, label "Ejecutar varias veces al dia"

At the bottom, a highlighted rule appears:
"La IA es el ultimo paso, no el primero"

Style: professional product architecture slide, modern, crisp typography, developer-friendly, no excessive decorations, no bullet overload. 

Animation: cards appear sequentially from left to right, then the bottom rule fades in with a green underline.
Duration: 22 seconds, 16:9.
```

## Texto exacto para postproduccion

```text
TASK
1. Recolectar noticias
2. Filtrar, deduplicar, clasificar y rankear
3. Presentar briefs relevantes
4. Ejecutar varias veces al dia

Regla clave:
La IA es el ultimo paso, no el primero.
```

## Voz sugerida

"Para resolverlo necesitabamos cuatro piezas: un scraper, un pipeline de procesamiento, una interfaz web y un scheduler. La decision mas importante fue que la IA no debia ser el primer paso. Debia ser el ultimo."

---

# 4. ACTION - Arquitectura general

## Objetivo

Mostrar arquitectura sin abrumar: React, FastAPI, PostgreSQL, scrapers, LLM providers, scheduler.

## Prompt video

```text
Create an animated system architecture diagram for EcoBrief Bolivia. Use a clean dark background and professional node-based diagram. Show these components as connected modules:

Frontend React + Vite
Backend FastAPI
PostgreSQL
Scrapers
LLM Providers: Groq, OpenAI, GitHub Models
Scheduler / Cron
Distribution: Email, Telegram, WhatsApp

Animate data flow: Scrapers -> FastAPI -> PostgreSQL -> processing pipeline -> LLM providers -> summaries -> React dashboard -> distribution channels.

Style: premium technical presentation, elegant, readable, minimal, green highlight for active flow, gray for inactive modules. No tiny unreadable text. No fake code blocks. 

Camera: slight parallax movement, nodes connect with animated green lines.

Duration: 25 seconds, 16:9.
```

## Texto para postproduccion

```text
Arquitectura
React + Vite | FastAPI | PostgreSQL | Scrapers | LLM Providers | Scheduler
```

## Voz sugerida

"La solucion se construyo como una aplicacion completa: frontend React con Vite, backend Python con FastAPI, PostgreSQL, scraping con httpx y BeautifulSoup, y proveedores de IA abstraidos detras de un cliente comun."

---

# 5. ACTION - Pipeline antes de IA

## Objetivo

Esta es la escena central. Debe mostrar que el valor tecnico esta en filtrar antes de llamar al LLM.

## Prompt video

```text
Create a professional animated data pipeline for EcoBrief Bolivia. News articles enter from the left as many small cards. They pass through sequential processing gates:

1. Scraping
2. Quality Filter
3. Deduplication
4. Classification
5. Ranking
6. Candidate Selection
7. AI Summary

Show many article cards entering, then fewer cards after each gate. Duplicates merge, low-quality cards fade out, categories get colored tags, ranking adds score badges, and only a small curated set reaches the AI Summary module.

Important: visually emphasize that AI is near the end, not at the beginning. The AI module should activate only after the previous gates finish.

Style: developer-friendly motion graphics, clean UI, dark navy background, green active flow, white article cards, category tags for Economia, Politica, Deportes, Tecnologia, Entretenimiento. Professional, not cartoonish.

On-screen minimal labels only. Use clear icons: scraper, funnel, duplicate merge, category tags, score gauge, shortlist, AI spark.

Duration: 35 seconds, 16:9.
```

## Texto para postproduccion

```text
Pipeline Zero-Waste
Scraping -> Filtro -> Deduplicacion -> Clasificacion -> Ranking -> Seleccion -> IA

No resumimos todo.
Resumimos lo mas relevante.
```

## Voz sugerida

"Primero recolectamos noticias desde fuentes configuradas. Luego descartamos articulos sin contenido suficiente, deduplicamos por URL, titulo y huella historica, clasificamos por categoria y rankeamos cada noticia con un score de relevancia. Hasta este punto, no usamos LLM para resumir. El objetivo no es resumir todo, sino resumir lo mas relevante."

## Variante mas tecnica para audiencia dev

```text
Create a split-screen animation: left side shows article cards moving through a visual pipeline; right side shows small clean pseudo-code snippets and config files: sources.yaml, classification.yaml, scoring.yaml. Keep snippets abstract and readable only as labels, not real code. Highlight deterministic processing before LLM invocation.

Show labels:
"URL hash"
"Fuzzy title"
"SHA-256 fingerprint"
"Weighted classification"
"Score 0-100"

Duration: 35 seconds, professional developer conference style.
```

---

# 6. ACTION - Ranking y score

## Objetivo

Explicar los factores de ranking de manera visual, no como tabla pesada.

## Prompt video

```text
Create a polished animated scoring dashboard for news ranking. Show one news article card in the center. Around it, seven scoring factors appear as radial modules with percentage weights:

Actualidad 15%
Relevancia local 20%
Impacto informativo 20%
Calidad 17%
Fuente 10%
Corroboracion 10%
Confianza categoria 8%

Each factor contributes to a circular score gauge that rises from 0 to 87/100. Then small penalty chips appear below: "texto corto", "sin fecha", "fuente desconocida", but only as subtle examples, not too many.

Style: sleek analytics UI, dark background, green score, yellow/gray minor penalties, crisp typography, professional SaaS dashboard.

Duration: 22 seconds, 16:9.
```

## Texto para postproduccion

```text
Ranking de relevancia
Score 0-100

Actualidad | Relevancia local | Impacto | Calidad | Fuente | Corroboracion | Confianza
```

## Voz sugerida

"El ranking usa factores como actualidad, relevancia local para Bolivia, impacto informativo, calidad del contenido, fuente, corroboracion y confianza de categoria. Tambien aplica penalizaciones cuando falta contenido, fecha o contexto boliviano."

---

# 7. ACTION - Uso responsable de IA y proveedores

## Objetivo

Mostrar LLM como recurso controlado, con router/fallback, sin entrar demasiado en tecnicismo.

## Prompt video

```text
Create an elegant animation showing responsible AI usage in EcoBrief Bolivia. A small curated set of article cards reaches an "LLM Router" module. The router has three provider lanes:

Groq
OpenAI
GitHub Models

The default lane is Groq. If rate limit appears, the flow smoothly switches to another provider lane. Show this as professional infrastructure routing, not as a dramatic failure.

Before the router, show three checkmarks:
"Filtrado"
"Deduplicado"
"Rankeado"

After the router, show clean brief cards generated with concise summaries and a "source" link indicator.

Style: modern cloud architecture, responsible AI, Green Tech, clean dark UI, green active lines, no excessive AI magic visuals.

Duration: 28 seconds, 16:9.
```

## Texto para postproduccion

```text
IA responsable
Filtrar -> Deduplicar -> Rankear -> Resumir

Groq | OpenAI | GitHub Models
```

## Voz sugerida

"Recien despues del filtro, la deduplicacion y el ranking llamamos al modelo. Los proveedores principales del documento son Groq, OpenAI y GitHub Models. Todos estan detras de una capa comun, asi que el sistema puede cambiar de proveedor sin modificar el resto de la aplicacion."

## Nota si quieres mencionar Nvidia en vivo

No lo pongas en pantalla principal si quieres alinearte al documento final. Si te preguntan:

```text
La documentacion final destaca Groq, OpenAI y GitHub Models. En la implementacion tambien se dejo soporte para otros proveedores compatibles con API estilo OpenAI, como Nvidia.
```

---

# 8. RESULT - Producto funcionando

## Objetivo

Mostrar una demo visual del MVP: home, recolectadas, datos, impacto, suscripcion.

## Prompt video

```text
Create a professional product demo animation for a web app called EcoBrief Bolivia. Show a clean browser window with a modern dashboard. Animate navigation through five sections:

Home: summarized top news cards
Recolectadas: raw collected news with source, date, image
Datos: economic indicators and useful external data
Impacto: Green Tech metrics dashboard
Suscripcion: preferences form with categories, frequency and channel

Use realistic UI but do not include too much readable text. Keep cards clean and polished. Use Spanish short labels. 

Style: production-ready SaaS demo, React dashboard aesthetic, white content panels on light gray background, green accents, professional, credible. 

Camera: smooth screen capture style with zooms and pans, not shaky.

Duration: 30 seconds, 16:9.
```

## Texto para postproduccion

```text
MVP funcional
Home | Noticias recolectadas | Datos | Impacto | Suscripcion
```

## Voz sugerida

"El MVP ya esta funcional y desplegado. Tiene scraping real, resumenes con IA, frontend web, noticias recolectadas con trazabilidad, pagina de datos, panel de impacto y suscripcion por preferencias."

---

# 9. RESULT - Metricas de impacto

## Objetivo

Hacer memorable el resultado: 174 a 39, 77.6% reduccion, 135 paginas evitadas, 67.5 minutos ahorrados.

## Prompt video

```text
Create a high-impact animated metrics scene for EcoBrief Bolivia. Show a funnel visualization:

174 noticias recolectadas
173 articulos utiles
169 articulos unicos
39 briefs generados

Then show three large metric cards:
135 paginas evitadas
67.5 minutos ahorrados
77.6% reduccion

Make the animation feel like a credible analytics dashboard, not a flashy marketing ad. Use clean counters counting up, green progress bars, and a subtle Bolivia outline in the background.

Style: professional Green Tech impact report, dark navy and white UI, green highlights, crisp typography. 

Duration: 25 seconds, 16:9.
```

## Texto exacto para postproduccion

```text
Corrida real - 15 de junio de 2026

174 recolectadas
173 utiles
169 unicas
39 briefs

135 paginas evitadas
67.5 minutos ahorrados
77.6% de reduccion
```

## Voz sugerida

"Una corrida real del 15 de junio de 2026 proceso 174 noticias y genero 39 briefs. Eso representa 135 paginas evitadas, 67.5 minutos estimados de lectura ahorrados y 77.6% de reduccion del flujo informativo."

---

# 10. RESULT - Canales y roadmap

## Objetivo

Mostrar distribucion y trabajo futuro sin que parezca una lista pendiente.

## Prompt video

```text
Create a professional roadmap and distribution animation. Show EcoBrief brief cards being prepared for three delivery channels:

Email
Telegram
WhatsApp

Represent Email as active but paused for personal account reasons, Telegram as in progress/free channel, WhatsApp as optional due to per-message cost. Use subtle status indicators, not warning-heavy visuals.

Then transition to a clean roadmap with three horizons:
Corto plazo: analiticas y mejoras de metricas
Mediano plazo: activar Telegram y WhatsApp
Largo plazo: entidades estatales, suscripcion, panel institucional

Style: executive technical roadmap, clean, calm, professional, no clutter.
Duration: 22 seconds, 16:9.
```

## Texto para postproduccion

```text
Distribucion personalizada
Email | Telegram | WhatsApp

Roadmap
Corto: metricas y analiticas
Mediano: canales en produccion
Largo: panel institucional y suscripcion
```

## Voz sugerida

"Email funciona con Gmail App Password, pero esta desactivado porque usa una cuenta personal. WhatsApp esta planteado con Twilio, pero tiene costo por mensaje. Telegram esta en proceso para activarlo como canal gratuito."

---

# 11. CIERRE - Mensaje final

## Objetivo

Cerrar con una imagen simple y fuerte: menos ruido, mas informacion esencial.

## Prompt video

```text
Create a cinematic closing scene for EcoBrief Bolivia. Start with noisy floating news cards around the character. The noise slowly compresses into a small clean stack of summarized brief cards. The character looks calm and focused, closes unnecessary tabs, and the EcoBrief Bolivia dashboard remains on screen with a clean green signal line.

Background: subtle outline of Bolivia, modern workspace, Green Tech feel. 

Mood: calm, confident, professional.

On-screen final quote:
"IA no para producir mas ruido, sino para reducirlo."

Then show:
"EcoBrief Bolivia"

Duration: 12 seconds, 16:9.
```

## Texto para postproduccion

```text
IA no para producir mas ruido,
sino para reducirlo.

EcoBrief Bolivia
```

## Voz sugerida

"EcoBrief Bolivia convierte un problema cotidiano, el exceso de informacion repetida, en una solucion Green Tech concreta. Usamos IA no para producir mas ruido, sino para reducirlo."

---

# Prompts para imagenes clave

Si prefieres generar imagenes fijas y animarlas despues, usa estos prompts.

## Imagen 1 - Usuario saturado

```text
Professional cinematic image of a Bolivian young software engineer at a desk, overwhelmed by TV news, phone social media scrolling, browser tabs, radio waveform and floating news cards. Modern realistic style, dark navy and green color accents, evening lighting, developer workspace, serious professional mood, no logos, no readable long text.
```

## Imagen 2 - Pipeline EcoBrief

```text
Clean professional data pipeline visualization for EcoBrief Bolivia: many news cards enter from the left, pass through gates labeled Scraping, Filter, Deduplication, Classification, Ranking, AI Summary, and only a few brief cards exit. Dark navy background, green active flow, SaaS dashboard style, crisp modern typography, developer presentation quality.
```

## Imagen 3 - Metricas

```text
Professional Green Tech analytics dashboard showing EcoBrief Bolivia impact metrics: 174 collected news, 39 briefs, 135 pages avoided, 67.5 minutes saved, 77.6% reduction. Clean data visualization, dark navy and white panels, green highlights, subtle Bolivia outline, polished product demo style.
```

## Imagen 4 - Cierre

```text
Cinematic closing image for EcoBrief Bolivia: noisy news cards compress into a clean concise brief dashboard, Bolivian software engineer calm and focused, modern workspace, Green Tech atmosphere, dark navy background, ecological green signal line, professional and inspiring but not exaggerated.
```

---

# Prompt maestro para generar una presentacion completa

Si una plataforma acepta generar video largo por secciones, usa este prompt.

```text
Create a professional animated presentation video for "EcoBrief Bolivia", a Green Tech news summarization platform from Bolivia. The presentation must follow the STAR method and feel like a polished developer conference product pitch, not a generic slide deck.

Visual style: cinematic but professional, modern SaaS UI, dark navy background, ecological green accents, clean typography, subtle Bolivia context, realistic recurring Bolivian young software engineer character, no childish cartoon, no excessive sci-fi, no fake logos, no clutter.

Structure:
1. Intro: EcoBrief Bolivia, responsible AI to reduce digital information waste.
2. Situation: a user tries to stay informed using TV, radio, news websites and endless social media scrolling; he becomes overwhelmed.
3. Situation: show digital information waste: duplicate articles, wasted time, mobile data, ads, fragmented sources.
4. Task: animated four-card slide: collect news, filter/deduplicate/classify/rank, present relevant briefs, run several times per day. Highlight: "AI is the last step, not the first."
5. Action: architecture diagram: React + Vite frontend, FastAPI backend, PostgreSQL, scrapers, LLM providers Groq/OpenAI/GitHub Models, scheduler, distribution channels.
6. Action: animated pipeline where many news cards pass through scraping, quality filter, deduplication, classification, ranking, candidate selection, then AI summary. Show fewer cards after each gate.
7. Action: responsible AI usage: only filtered and ranked candidates reach the LLM router; show Groq, OpenAI and GitHub Models as provider lanes.
8. Result: product demo with pages Home, collected news, data, impact metrics, subscription preferences.
9. Result: impact metrics funnel: 174 collected, 173 useful, 169 unique, 39 briefs, 135 pages avoided, 67.5 minutes saved, 77.6% reduction.
10. Closing: noisy news compresses into clean briefs. Final message: "IA no para producir mas ruido, sino para reducirlo."

Keep on-screen text minimal, readable and in Spanish. Use smooth transitions and professional pacing. Duration target: 4 minutes, 16:9, high resolution.
```

---

# Recomendaciones de produccion

1. Genera cada escena por separado. Las plataformas IA mantienen mejor calidad en clips de 8 a 30 segundos.
2. No dependas de texto generado por video IA para cifras importantes. Agrega cifras y titulos en postproduccion.
3. Mantén el mismo personaje usando siempre la misma descripcion.
4. Usa la misma paleta en todos los clips: navy, gris, blanco y verde.
5. Para audiencia developer, prioriza diagramas limpios y flujo de datos antes que metaforas demasiado abstractas.
6. En las escenas tecnicas, usa etiquetas cortas: `FastAPI`, `React`, `PostgreSQL`, `Scraping`, `Ranking`, `LLM Router`.
7. Evita mostrar marcas reales de medios de comunicacion. Usa fuentes genericas para no distraer.
8. Si una herramienta genera texto raro, pide "no text" y agrega todo el texto manualmente.

