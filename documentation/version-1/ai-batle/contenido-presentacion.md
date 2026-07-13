# Contenido de Presentacion - EcoBrief Bolivia
## Basado en `script-1-0-1.md`

Propuesta para una presentacion profesional, sobria y tecnica sin exceso de texto.

Paleta recomendada:

- **Azul profundo:** `#1e3a5f`
- **Verde EcoBrief:** `#16a34a`

Regla visual: usar blanco/grises solo como fondo o texto neutro; los colores de marca deben limitarse a azul profundo y verde.

---

## Slide 1 - Portada

**Titulo:** EcoBrief Bolivia

**Subtitulo:** IA responsable para reducir el desperdicio digital informativo

**Contenido visual sugerido:**

- Logo o nombre del proyecto.
- Silueta sutil de Bolivia o dashboard minimalista.
- Frase corta: "Menos ruido. Mas informacion esencial."

**Notas de orador:**

Hola, buenas tardes a todos. Hoy les presento EcoBrief Bolivia, una plataforma que usa inteligencia artificial responsable para reducir el desperdicio digital informativo.

---

## Slide 2 - Situation: el problema cotidiano

**Titulo:** Queremos estar informados

**Mensaje principal:** El acceso a noticias esta fragmentado.

**Contenido en pantalla:**

- TV y noticieros
- Radio
- Sitios web
- Redes sociales
- Multiples titulares

**Apoyo visual:**

Una persona intentando informarse desde varias fuentes al mismo tiempo.

**Notas de orador:**

Muchas personas queremos estar informadas sobre politica, economia, deportes, tecnologia y entretenimiento. Pero para lograrlo abrimos varios medios, vemos noticieros, escuchamos radio o scrolleamos redes sociales durante mucho tiempo.

---

## Slide 3 - Situation: desperdicio digital informativo

**Titulo:** El costo oculto de informarse

**Mensaje principal:** No solo consumimos noticias; tambien consumimos tiempo, datos y atencion.

**Contenido en pantalla:**

| Desperdicio | Ejemplo |
|---|---|
| Tiempo | Comparar titulares repetidos |
| Datos | Cargar paginas completas |
| Atencion | Scrollear sin fin |
| Confianza | Contenido sin fuente clara |

**Notas de orador:**

Leemos la misma noticia repetida en distintos medios, cargamos paginas con publicidad e imagenes, perdemos tiempo comparando titulares y consumimos informacion fragmentada.

---

## Slide 4 - Pregunta guia

**Titulo:** La pregunta

**Mensaje central grande:**

**Como reducimos el ruido sin dejar de informarnos?**

**Contenido secundario:**

Una solucion util no debe crear mas contenido. Debe reducir el contenido innecesario.

**Notas de orador:**

La pregunta fue como reducir ese tiempo, ese consumo de datos y ese ruido, pero seguir informados con contenido confiable.

---

## Slide 5 - Task: lo que habia que construir

**Titulo:** Cuatro piezas necesarias

**Contenido en pantalla:**

1. Recolectar noticias desde fuentes bolivianas.
2. Filtrar, deduplicar, clasificar y rankear.
3. Presentar briefs relevantes al usuario.
4. Ejecutar el proceso varias veces al dia.

**Frase destacada:**

**La IA es el ultimo paso, no el primero.**

**Notas de orador:**

Para resolverlo, necesitabamos un scraper, un pipeline, una interfaz y un scheduler. La decision mas importante fue que la IA no debia ser el primer paso.

---

## Slide 6 - Action: arquitectura general

**Titulo:** Arquitectura del sistema

**Contenido en pantalla:**

```text
Scrapers -> FastAPI -> PostgreSQL -> React
                 |
             LLM Provider
                 |
        Groq / OpenAI / GitHub Models
```

**Tecnologias clave:**

- Backend: Python 3.11 + FastAPI
- Frontend: React + Vite + TypeScript
- Base de datos: PostgreSQL
- Scraping: httpx + BeautifulSoup + lxml
- Infraestructura: Docker + VPS

**Graficos PlantUML sugeridos:**

- Detallado: `documentation/version-1/ai-batle/system-architecture-detailed.puml`
- Simplificado: `documentation/version-1/ai-batle/system-architecture-simple.puml`

**Notas de orador:**

La solucion se construyo como una aplicacion completa. El backend con FastAPI orquesta scraping, procesamiento, persistencia, metricas y distribucion.

---

## Slide 7 - Action: pipeline zero-waste

**Titulo:** Pipeline antes de IA

**Contenido en pantalla:**

```text
Fuentes
  -> Scraping
  -> Filtro de calidad
  -> Deduplicacion
  -> Clasificacion
  -> Ranking
  -> Seleccion
  -> IA
```

**Grafico PlantUML sugerido:**

`documentation/version-1/ai-batle/pipeline-zero-waste.puml`

**Version simplificada para slide:**

`documentation/version-1/ai-batle/pipeline-simple.puml`

**Diagramas por fase:**

- Recoleccion: `documentation/version-1/ai-batle/pipeline-phase-01-recoleccion.puml`
- Filtrado y deduplicacion: `documentation/version-1/ai-batle/pipeline-phase-02-filtrado-deduplicacion.puml`
- Clasificacion y priorizacion: `documentation/version-1/ai-batle/pipeline-phase-03-clasificacion-priorizacion.puml`
- Generacion y distribucion: `documentation/version-1/ai-batle/pipeline-phase-04-generacion-distribucion.puml`

**Frase destacada:**

No resumimos todo. Resumimos lo mas relevante.

**Notas de orador:**

Primero recolectamos noticias desde fuentes configuradas. Luego descartamos contenido pobre, deduplicamos, clasificamos y rankeamos. Solo despues seleccionamos candidatos para IA.

---

## Slide 8 - Action: deduplicacion y clasificacion

**Titulo:** Menos ruido antes del modelo

**Contenido en pantalla:**

**Deduplicacion**

- URL hash
- Titulo normalizado
- Huella historica SHA-256

**Clasificacion**

- Economia
- Politica
- Deportes
- Tecnologia
- Entretenimiento

**Notas de orador:**

La deduplicacion evita procesar la misma noticia varias veces. La clasificacion usa reglas ponderadas por titulo, descripcion, contenido y categoria de la fuente.

---

## Slide 9 - Action: ranking de relevancia

**Titulo:** Score de prioridad

**Mensaje principal:** Cada noticia recibe un puntaje de 0 a 100.

**Contenido en pantalla:**

| Factor | Peso |
|---|---:|
| Relevancia local | 20% |
| Impacto informativo | 20% |
| Calidad del contenido | 17% |
| Actualidad | 15% |
| Fuente | 10% |
| Corroboracion | 10% |
| Confianza de categoria | 8% |

**Notas de orador:**

El ranking prioriza noticias recientes, relevantes para Bolivia, con impacto informativo y contenido suficiente. Tambien penaliza texto corto, falta de fecha o bajo contexto local.

---

## Slide 10 - Action: IA responsable

**Titulo:** IA solo cuando aporta valor

**Contenido en pantalla:**

```text
Filtrado -> Deduplicado -> Rankeado -> Resumido
```

**Proveedores documentados:**

- Groq
- OpenAI
- GitHub Models

**Frase destacada:**

Cada articulo filtrado antes de IA es una llamada menos al modelo.

**Notas de orador:**

Recien despues del filtro, la deduplicacion y el ranking llamamos al modelo. Todos los proveedores estan detras de una capa comun, asi que el sistema puede cambiar sin modificar el resto de la aplicacion.

---

## Slide 11 - Result: MVP funcional

**Titulo:** Producto desplegado

**Contenido en pantalla:**

- Scraping real de fuentes bolivianas.
- Resumenes generados con IA.
- Frontend web con noticias destacadas.
- Noticias recolectadas con fuente e imagen.
- Pagina de datos.
- Panel de impacto.
- Suscripcion por preferencias.

**URL:**

`https://briefs.ecobriefbolivia.online/`

**Notas de orador:**

El MVP ya esta funcional y desplegado. Tiene scraping real, resumenes con IA, frontend web, pagina de datos, metricas y suscripcion.

---

## Slide 12 - Result: impacto medible

**Titulo:** Resultado de una corrida real

**Contenido en pantalla:**

**15 de junio de 2026**

| Metrica | Valor |
|---|---:|
| Noticias recolectadas | 174 |
| Articulos utiles | 173 |
| Articulos unicos | 169 |
| Briefs generados | 39 |
| Paginas evitadas | 135 |
| Minutos ahorrados | 67.5 |
| Reduccion | 77.6% |

**Notas de orador:**

Una corrida real proceso 174 noticias y genero 39 briefs. Esto representa 135 paginas evitadas, 67.5 minutos estimados de lectura ahorrados y 77.6% de reduccion del flujo informativo.

---

## Slide 13 - Result: demo guiada

**Titulo:** Recorrido del producto

**Contenido en pantalla:**

1. Home: briefs principales.
2. Noticias recolectadas: fuente, imagen y fecha.
3. Datos: indicadores externos.
4. Impacto: metricas globales y por corrida.
5. Suscripcion: categorias, frecuencia y canal.

**Notas de orador:**

Para la demo mostraria primero el home, luego las noticias recolectadas, despues datos, impacto y finalmente suscripcion.

---

## Slide 14 - Canales y siguientes pasos

**Titulo:** Distribucion personalizada

**Contenido en pantalla:**

| Canal | Estado |
|---|---|
| Email | Funcional, pausado por cuenta personal |
| Telegram | En integracion |
| WhatsApp | Planteado con Twilio, pausado por costo |

**Roadmap breve:**

- Corto plazo: metricas y analiticas.
- Mediano plazo: canales en produccion.
- Largo plazo: panel institucional y suscripcion.

**Notas de orador:**

Email funciona, pero esta desactivado por usar una cuenta personal. WhatsApp tiene costo por mensaje. Telegram es el canal mas conveniente para activar como siguiente paso.

---

## Slide 15 - Cierre

**Titulo:** Menos ruido. Mas informacion esencial.

**Mensaje final:**

**EcoBrief Bolivia usa IA no para producir mas ruido, sino para reducirlo.**

**Contenido secundario:**

- Menos paginas abiertas.
- Menos duplicidad.
- Menos llamadas innecesarias a IA.
- Mas informacion trazable.

**Notas de orador:**

EcoBrief Bolivia convierte un problema cotidiano, el exceso de informacion repetida, en una solucion Green Tech concreta. Usamos IA de forma responsable, despues de filtrar, deduplicar y priorizar.

---

## Recomendaciones de diseno

- Usar maximo dos colores de marca: azul profundo y verde.
- Evitar fondos recargados.
- No llenar slides con parrafos.
- Usar tablas solo cuando el dato sea importante.
- Mantener una idea principal por slide.
- Agregar animaciones simples: aparecer, desplazamiento suave, contador o resaltado.
- Evitar degradados fuertes y paletas multicolor.
- Para la demo, usar capturas reales si estan disponibles.
