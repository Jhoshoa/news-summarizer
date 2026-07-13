# Script de Presentacion - EcoBrief Bolivia
## AI Battle - Josoe Ichuta (STAR Method - v1.0.1)

---

## Veredicto rapido sobre tu script actual

Tu script si se alinea con el documento `preview-final-doc.tex` en la idea central:

- EcoBrief Bolivia reduce el desperdicio digital informativo.
- El pipeline recolecta, filtra, deduplica, clasifica, rankea y recien despues usa IA.
- El sistema tiene frontend React, backend FastAPI, PostgreSQL, scraping real, metricas y suscripcion.
- Las metricas principales del documento son: 174 noticias recolectadas, 39 briefs generados, 135 paginas evitadas, 67.5 minutos ahorrados y 77.6% de reduccion.

Pero hay ajustes importantes:

- Cambiar "Flask" por **FastAPI**. El documento y el codigo usan FastAPI.
- No presentar Nvidia/Mistral como proveedor principal del documento final. El documento oficial habla de **Groq, OpenAI y GitHub Models**. El codigo soporta Nvidia, pero para la presentacion conviene decirlo solo como fallback tecnico opcional si te preguntan.
- Reforzar el mensaje Green Tech: no es solo resumir noticias, es reducir paginas cargadas, datos consumidos, duplicidad y llamadas innecesarias a IA.
- Evitar decir "todo es Python puro" si mencionas librerias externas. Mejor: "hasta aqui no usamos LLM; usamos logica deterministica en Python".
- Usar las horas documentadas/configuradas con cuidado. Puedes decir "horarios configurables, por ejemplo manana, tarde y noche", salvo que en tu ambiente real tengas 8, 10, 13 y 17.

---

## Estructura sugerida

| Bloque | Metodo STAR | Tiempo |
|---|---:|---:|
| Problema | Situation | 1.5 min |
| Reto tecnico | Task | 1.5 min |
| Pipeline y arquitectura | Action | 4.5 min |
| Impacto y demo | Result | 2 min |
| Cierre | Mensaje final | 0.5 min |

---

## 1. SITUATION - El problema

Hola, buenas tardes a todos.

Hoy les presento **EcoBrief Bolivia**, una plataforma que usa inteligencia artificial responsable para reducir el desperdicio digital informativo.

El problema que vimos es simple: muchas personas queremos estar informadas sobre lo que pasa en Bolivia y en el mundo: politica, economia, deportes, tecnologia, entretenimiento. Pero para lograrlo normalmente abrimos varios medios, vemos noticieros, escuchamos radio o scrolleamos redes sociales durante mucho tiempo.

Y ahi aparece el desperdicio digital:

- Leemos la misma noticia repetida en distintos medios.
- Cargamos paginas completas con publicidad, imagenes y scripts.
- Perdemos tiempo comparando titulares.
- Consumimos informacion fragmentada, muchas veces sin una fuente clara.

Entonces la pregunta fue:

**Como podemos reducir ese tiempo, ese consumo de datos y ese ruido, pero seguir informados con contenido confiable?**

---

## 2. TASK - Lo que habia que construir

Para resolverlo, necesitabamos construir cuatro piezas:

1. Un **web scraper** que recolecte noticias desde fuentes bolivianas configuradas.
2. Un **pipeline de procesamiento** que filtre, deduplique, clasifique y rankee noticias antes de usar IA.
3. Una **interfaz web** para mostrar los briefs mas relevantes, las noticias recolectadas y las metricas.
4. Un **scheduler** o cron job para ejecutar el proceso varias veces al dia en horarios utiles.

La decision mas importante fue esta:

**La IA no debia ser el primer paso. Debia ser el ultimo paso.**

Primero limpiamos, deduplicamos y priorizamos con codigo. Solo despues mandamos a un modelo lo que realmente vale la pena resumir.

---

## 3. ACTION - Arquitectura general

La solucion se construyo como una aplicacion completa:

- **Backend:** Python 3.11 con FastAPI.
- **Frontend:** React con Vite y TypeScript.
- **Base de datos:** PostgreSQL.
- **Scraping:** `httpx`, `BeautifulSoup4` y `lxml`.
- **IA:** Groq, OpenAI y GitHub Models, abstraidos detras de un cliente comun.
- **Infraestructura:** Docker y un VPS de Hostinger.

El backend orquesta todo el proceso. Expone endpoints para el frontend, ejecuta el pipeline, guarda resultados, calcula metricas y prepara la distribucion por canales como email, Telegram y WhatsApp.

---

## 4. ACTION - Pipeline antes de usar IA

El pipeline funciona asi:

```text
Fuentes de noticias
    -> scraping
    -> filtro de calidad
    -> deduplicacion
    -> clasificacion
    -> ranking
    -> seleccion de candidatos
    -> IA para resumen
    -> metricas y distribucion
```

Primero recolectamos noticias desde fuentes configuradas en `config/sources.yaml`. Cada fuente tiene selectores para titulo, URL, fecha, imagen y contenido. Si una pagina cambia su HTML, el scraper tiene un fallback generico para seguir extrayendo enlaces que parezcan articulos periodisticos.

Despues aplicamos filtros deterministas:

- Se descartan articulos sin contenido suficiente.
- Se deduplican noticias por URL.
- Se normalizan titulos y se comparan con similitud para detectar repetidos.
- Se calcula una huella historica con SHA-256 para detectar historias equivalentes entre corridas.

Luego clasificamos cada noticia en categorias como economia, politica, deportes, tecnologia y entretenimiento.

La clasificacion usa reglas ponderadas:

- Titulo por 3.
- Descripcion por 2.
- Contenido por 1.
- Categoria de la fuente por 2.5.

Si la confianza es baja, el sistema puede recurrir a un LLM como fallback, pero solo en casos ambiguos.

Despues viene el ranking. Cada noticia recibe un score de 0 a 100 usando factores como:

- Actualidad.
- Relevancia local para Bolivia.
- Impacto informativo.
- Calidad del contenido.
- Confiabilidad de la fuente.
- Corroboracion por varias fuentes.
- Confianza de categoria.

Tambien hay penalizaciones por contenido muy corto, falta de fecha, fuente desconocida o noticias internacionales sin contexto boliviano.

Hasta este punto, el objetivo es claro:

**No resumir todo. Resumir solo lo mas relevante.**

---

## 5. ACTION - Uso responsable de IA

Recien despues del filtro, la deduplicacion y el ranking seleccionamos los mejores candidatos.

La seleccion usa limites por categoria. Por ejemplo, deportes, tecnologia y entretenimiento pueden tener menos candidatos, mientras politica y economia pueden tener un limite mayor porque suelen tener mas impacto nacional.

Antes de generar un resumen se vuelve a validar:

- Si la noticia ya fue resumida antes.
- Si existe una historia equivalente en la base de datos.
- Si entre los candidatos hay noticias que hablan del mismo hecho.

Solo despues se llama al modelo de IA.

El documento final define tres proveedores principales:

| Proveedor | Uso |
|---|---|
| Groq | Opcion gratuita y rapida |
| OpenAI | Mayor capacidad cuando se requiere |
| GitHub Models | Alternativa con cuota diaria |

Todos estan detras de una capa llamada `LLMProvider`, asi que el resto del sistema no depende directamente de un proveedor especifico.

La idea Green Tech aqui es importante:

**Cada articulo que filtramos antes de IA es una llamada menos al modelo, menos tokens procesados y menos desperdicio computacional.**

---

## 6. RESULT - Lo que ya existe

El MVP ya esta funcional y desplegado en un VPS de Hostinger con dominio propio:

`https://briefs.ecobriefbolivia.online/`

Actualmente cuenta con:

- Scraping real de fuentes bolivianas.
- Clasificacion, deduplicacion y ranking.
- Resumenes generados con IA.
- Frontend web con noticias destacadas.
- Vista de noticias recolectadas con fuente, imagen y fecha.
- Pagina de datos con indicadores externos.
- Panel de impacto Green Tech.
- Pagina de suscripcion y preferencias.
- Pruebas automatizadas con pytest.

Una corrida real del 15 de junio de 2026 mostro estos resultados:

```text
174 noticias recolectadas
173 articulos utiles
169 articulos unicos
39 briefs generados
135 paginas evitadas
67.5 minutos estimados de lectura ahorrados
77.6% de reduccion del flujo informativo
```

Esto demuestra que EcoBrief no solo genera resumenes. Tambien mide cuanto ruido digital se evita.

---

## 7. RESULT - Demo guiada

Para la demo, mostraria este recorrido:

1. **Home:** noticias resumidas y principales.
2. **Noticias recolectadas:** fuente, imagen, fecha y trazabilidad.
3. **Datos:** indicadores externos y datos utiles agregados.
4. **Impacto:** metricas globales y por corrida del pipeline.
5. **Suscripcion:** preferencias por categoria, frecuencia y canal.

Sobre los canales:

- Email funciona con Gmail App Password, pero esta desactivado porque usa una cuenta personal.
- WhatsApp esta planteado con Twilio, pero se mantiene desactivado por costo por mensaje.
- Telegram esta en proceso de integracion para activarlo como canal gratuito.

Como mejora futura, se puede contratar un SMTP dedicado, activar Telegram en produccion y evaluar WhatsApp solo si el costo se justifica.

---

## 8. CIERRE

Para cerrar, diria:

EcoBrief Bolivia convierte un problema cotidiano, el exceso de informacion repetida, en una solucion Green Tech concreta.

Usamos IA, pero no para producir mas ruido. La usamos de forma responsable, despues de filtrar, deduplicar y priorizar.

El resultado es menos tiempo perdido, menos paginas abiertas, menos procesamiento innecesario y una forma mas clara de informarse.

**EcoBrief Bolivia usa IA no para producir mas ruido, sino para reducirlo.**

---

## Nota para preguntas tecnicas

Si te preguntan por Nvidia o Mistral, puedes responder asi:

"El documento final presenta Groq, OpenAI y GitHub Models como proveedores principales. En la implementacion tambien se dejo soporte para otros proveedores compatibles con API estilo OpenAI, como Nvidia, pero para la presentacion estoy destacando los proveedores documentados oficialmente."

Si te preguntan por los horarios:

"El scheduler permite configurar ventanas horarias. En el documento se describe como tareas repetidas o cron jobs; en despliegue se puede ajustar a horarios donde realmente hay noticias relevantes, por ejemplo manana, tarde y noche."

