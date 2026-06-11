# EcoBrief Bolivia

## IA responsable para reducir desperdicio digital informativo

**Equipo:** Josoe Ichuta, Ingenieria; Raquel Auza, Digital-Academy  
**Categoria propuesta:** Green Tech / sostenibilidad digital / uso eficiente de IA  
**Estado del proyecto:** prototipo funcional con backend, frontend, scraping, base de datos, resumen IA, ranking, deduplicacion y metricas de impacto.

---

## 1. Resumen ejecutivo

EcoBrief Bolivia es una plataforma que reduce el desperdicio digital informativo al convertir muchas noticias locales, repetidas y dispersas en briefs claros, priorizados y personalizados.

El sistema recopila noticias de medios bolivianos, extrae el contenido util, elimina duplicados, clasifica por categoria, prioriza por relevancia nacional y genera resumenes con IA solo despues de reducir el volumen de informacion. La propuesta no busca generar mas contenido: busca disminuir ruido, navegacion innecesaria, consumo de datos y procesamiento redundante.

Desde el enfoque Green Tech, EcoBrief Bolivia ataca un problema real de sostenibilidad digital: las personas revisan varios sitios, cargan paginas con imagenes, publicidad y scripts, leen titulares repetidos y consumen tiempo, datos y recursos digitales para llegar a la misma informacion. EcoBrief reduce ese flujo a una sintesis util y medible.

El prototipo ya cuenta con:

- Web scraping de fuentes locales.
- Limpieza y extraccion de contenido.
- Clasificacion automatica por categorias.
- Ranking de prioridad.
- Resumenes generados con IA.
- Deduplicacion por URL, titulo y huella historica de historia.
- Pagina de impacto con metricas de reduccion.
- Preferencias de usuario para categorias y frecuencia.
- Arquitectura lista para distribucion por WhatsApp y Telegram.

La tesis central del proyecto es:

> EcoBrief Bolivia usa IA de forma responsable para reducir contenido redundante, navegacion innecesaria y procesamiento digital repetido.

---

## 2. Problema

### 2.1 Sobrecarga informativa

Informarse sobre la actualidad boliviana suele requerir revisar multiples portales, comparar titulares, abrir articulos completos y descartar contenido repetido. Este proceso consume tiempo y atencion, especialmente cuando una misma noticia aparece en varias fuentes con titulos ligeramente distintos.

### 2.2 Duplicacion entre medios

Una misma historia puede aparecer:

- En medios distintos.
- Con URLs diferentes.
- Con titulos parecidos.
- Republicada en otro momento.
- Como nota relacionada dentro de otra noticia.

Sin deduplicacion, el usuario termina leyendo la misma historia varias veces y el sistema puede enviar contenido repetido a IA.

### 2.3 Navegacion y consumo de datos innecesarios

Cada visita a una pagina de noticias puede implicar descarga de HTML, imagenes, anuncios, scripts, trackers y recursos externos. Cuando el usuario abre varias paginas para entender un solo hecho, se produce desperdicio digital: datos transferidos, procesamiento del navegador, tiempo de pantalla y carga de servidores que podrian evitarse.

### 2.4 Uso ineficiente de IA

Usar IA directamente sobre todo lo recolectado es costoso e innecesario. Si se resumen articulos duplicados o de baja calidad, se desperdician tokens, llamadas al modelo y recursos computacionales.

EcoBrief Bolivia resuelve esto aplicando IA despues de filtrar, deduplicar, clasificar y priorizar.

---

## 3. Solucion propuesta

EcoBrief Bolivia funciona como una capa inteligente entre los medios de noticias y los usuarios.

El sistema realiza el siguiente flujo:

1. Recolecta noticias desde medios locales.
2. Extrae descripcion, cuerpo, imagen, fuente, categoria y fecha.
3. Filtra articulos sin contenido util.
4. Deduplica por URL, titulo y huella de historia.
5. Clasifica por categorias.
6. Calcula un ranking de prioridad.
7. Selecciona candidatos relevantes.
8. Resume con IA.
9. Guarda summaries y metricas.
10. Muestra resultados en la web y prepara distribucion personalizada.

**Diagrama sugerido:** insertar aqui `documentation/diagrams/pipeline.puml`.

---

## 4. Enfoque Green Tech

EcoBrief Bolivia se alinea con Green Tech desde la sostenibilidad digital.

### 4.1 Reduccion de desperdicio digital

El proyecto reduce operaciones innecesarias en el consumo de noticias:

- Menos paginas abiertas.
- Menos articulos repetidos.
- Menos contenido enviado a IA.
- Menos navegacion manual.
- Menos summaries duplicados.
- Menos ruido informativo.

### 4.2 Uso responsable de IA

La IA se usa solo cuando aporta valor. Antes de resumir, el sistema:

- Limpia el contenido.
- Descarta articulos sin cuerpo util.
- Deduplica noticias repetidas.
- Agrupa historias similares.
- Prioriza las noticias mas relevantes.
- Reutiliza summaries cacheados cuando corresponde.

Esto evita usar modelos generativos sobre informacion redundante.

### 4.3 Personalizacion para evitar consumo innecesario

El usuario puede definir categorias y frecuencia. Esto reduce el envio de informacion irrelevante y evita que la persona revise multiples sitios varias veces al dia.

---

## 5. Funcionamiento tecnico del sistema

### 5.1 Backend

El backend esta construido con FastAPI y Python. Se encarga de ejecutar el pipeline de noticias, exponer APIs, administrar suscripciones, calcular metricas y coordinar la generacion de resumenes.

Componentes principales:

- `collectors`: scraping y fuentes externas.
- `processors`: deduplicacion, clasificacion, ranking, resumen y reescritura.
- `llm`: integracion con proveedor IA.
- `db`: persistencia en PostgreSQL.
- `api`: endpoints para frontend.
- `distributors`: WhatsApp y Telegram.
- `scheduler`: ejecucion programada.

### 5.2 Frontend

El frontend permite explorar:

- Pagina principal con noticias priorizadas.
- Pagina de noticias.
- Detalle de articulo.
- Pagina de impacto.
- Pagina de suscripcion/preferencias.
- Indicadores economicos y clima como contexto local.

### 5.3 Base de datos

PostgreSQL almacena:

- Articulos recolectados.
- Fuentes.
- Categorias.
- Summaries.
- Suscriptores.
- Preferencias.
- Corridas del pipeline.
- Metricas de recoleccion y deduplicacion.

### 5.4 Deduplicacion historica

EcoBrief Bolivia no se limita a evitar URLs repetidas. Tambien calcula una huella de historia basada en:

- Titulo normalizado.
- Categoria.
- Fragmento de contenido normalizado.

Esto permite detectar noticias equivalentes aunque tengan URLs diferentes o hayan sido publicadas en momentos distintos.

Campos clave:

- `canonical_key`
- `content_fingerprint`
- `story_cluster_id`
- `duplicate_of_article_id`
- `duplicate_reason`
- `similarity_score`

---

## 6. Metricas de impacto

EcoBrief mide el impacto del pipeline y lo presenta como estimaciones transparentes. No se afirma una medicion energetica directa; se calcula reduccion operativa a partir del flujo real del sistema.

### 6.1 Metricas reales del sistema

Estas metricas salen del pipeline:

- Articulos recolectados.
- Articulos utiles despues del filtro de calidad.
- Articulos unicos despues de deduplicacion.
- Duplicados descartados.
- Articulos rankeados.
- Candidatos enviados a resumen.
- Summaries generados.
- Uso de cache.
- Duplicados historicos detectados.

### 6.2 Metricas estimadas de sostenibilidad digital

Estas metricas se calculan a partir de supuestos explicitos:

- Paginas evitadas.
- Minutos estimados ahorrados.
- MB estimados no descargados.
- Llamadas IA evitadas.
- Tasa de reduccion.

Formulas usadas:

```text
paginas_evitadas = articulos_recolectados - summaries_generados
minutos_ahorrados = paginas_evitadas * minutos_promedio_por_articulo
mb_ahorrados = paginas_evitadas * mb_promedio_por_pagina
tasa_reduccion = 1 - (summaries_generados / articulos_recolectados)
llamadas_ia_evitadas = duplicados_detectados + articulos_no_priorizados
```

Supuestos iniciales del prototipo:

```text
minutos_promedio_por_articulo = 0.5
mb_promedio_por_pagina = 0.8
```

Estos valores son conservadores y pueden ajustarse con mediciones reales en una fase posterior.

### 6.3 Interpretacion

La metrica mas importante no es prometer una cifra exacta de CO2. La contribucion Green Tech es demostrar que la arquitectura reduce operaciones digitales innecesarias antes de que ocurran:

- Menos articulos procesados por IA.
- Menos duplicados mostrados.
- Menos paginas que el usuario necesita abrir.
- Menos tiempo invertido en revisar informacion repetida.

**Diagrama sugerido:** insertar aqui `documentation/diagrams/impact-metrics.puml`.

---

## 7. Uso responsable de IA

EcoBrief aplica IA con un enfoque de eficiencia:

1. Primero recolecta y limpia.
2. Luego filtra articulos sin contenido.
3. Despues deduplica.
4. Luego clasifica y rankea.
5. Finalmente resume solo los candidatos relevantes.

Esto evita enviar todo el HTML o todo el lote recolectado al modelo.

Practicas implementadas:

- No se resume contenido vacio.
- No se resume cada URL recolectada.
- No se resumen duplicados historicos.
- Se reutilizan summaries recientes cuando aplica.
- Se reduce el numero de llamadas IA.
- Se conserva trazabilidad del pipeline.

Mensaje clave para jurado:

> EcoBrief no usa IA para producir mas ruido; usa IA para reducir ruido.

---

## 8. Costos

### 8.1 Costos actuales del prototipo

El prototipo esta disenado para operar con bajo costo:

| Componente | Estado actual | Costo aproximado |
|---|---:|---:|
| Backend FastAPI | Local/dev | Bajo |
| Frontend Vite/React | Local/dev | Bajo |
| PostgreSQL | Docker/local | Bajo |
| IA | Groq/free tier durante prototipo | Bajo o cero en demo |
| Scraping | Requests/Playwright segun fuente | Bajo |
| WhatsApp/Telegram | Preparado, depende de credenciales | Variable |

### 8.2 Costos si escala

En produccion, los costos principales serian:

- Hosting del backend.
- Base de datos PostgreSQL.
- Proveedor IA.
- Mensajeria WhatsApp si se usa Twilio u otro proveedor.
- Monitoreo y logs.

### 8.3 Estrategia de control de costos

EcoBrief reduce costos por diseno:

- Deduplicacion antes de IA.
- Ranking antes de IA.
- Cache de summaries.
- Limite de candidatos por categoria.
- Preferencias de usuario para no enviar contenido irrelevante.
- Posibilidad de usar modelos pequenos para clasificacion y modelos mejores solo para resumen.

### 8.4 Costo por resumen

El costo por resumen depende del proveedor IA y del volumen de tokens. La arquitectura reduce este costo porque no resume todo lo recolectado, sino solo un subconjunto priorizado.

Formula de estimacion:

```text
costo_total_ia = numero_de_llamadas * costo_promedio_por_llamada
costo_por_usuario = costo_total_ia / usuarios_activos
ahorro_por_dedupe = llamadas_evitas * costo_promedio_por_llamada
```

---

## 9. Estado actual del prototipo

### 9.1 Implementado

- Scraping de medios locales.
- Extraccion de titulo, URL, descripcion, cuerpo, imagen y fecha.
- Correccion de selectores para cambios en HTML de fuentes.
- Clasificacion por categorias.
- Ranking por relevancia.
- Deduplicacion dentro de corrida.
- Deduplicacion historica por historia.
- Resumen IA.
- Reescritura de summaries.
- Persistencia en PostgreSQL.
- Pagina Home.
- Pagina Noticias.
- Pagina Detalle.
- Pagina Impacto.
- Preferencias de suscripcion.
- Endpoint manual para generar resumenes.
- Preparacion para WhatsApp y Telegram.

### 9.2 Demo recomendada

Orden sugerido para video o presentacion en vivo:

1. Mostrar Home con noticias priorizadas.
2. Abrir una noticia y mostrar cuerpo/resumen.
3. Mostrar pagina de Noticias.
4. Ejecutar trigger manual de resumen.
5. Mostrar pagina de Impacto.
6. Mostrar preferencias de usuario.
7. Explicar que el sistema deduplica antes de resumir.

---

## 10. Diferenciadores

EcoBrief Bolivia se diferencia porque:

- No es solo un resumidor de noticias.
- Mide reduccion de flujo informativo.
- Deduplica antes de usar IA.
- Prioriza informacion relevante.
- Agrupa historias repetidas.
- Esta orientado a medios bolivianos.
- Permite personalizacion por categorias.
- Expone una narrativa Green Tech defendible con metricas.

Frase de posicionamiento:

> Noticias esenciales, menos ruido digital.

---

## 11. Limitaciones actuales

EcoBrief es un prototipo funcional, pero tiene limitaciones reconocidas:

- Las metricas de MB y tiempo son estimaciones, no mediciones energeticas directas.
- Los scrapers dependen de cambios en el HTML de las fuentes.
- La distribucion por WhatsApp requiere configuracion productiva y costos externos.
- No todos los articulos historicos tienen backfill de fingerprints.
- La agrupacion semantica avanzada aun no usa embeddings.
- La medicion de CO2 no esta implementada con metodologia certificada.

Estas limitaciones no invalidan el prototipo; delimitan el alcance actual y el roadmap de madurez.

---

## 12. Roadmap futuro

### 12.1 Corto plazo

- Backfill de fingerprints para articulos historicos.
- Mostrar en UI cuantas coberturas fueron agrupadas.
- Mejorar pagina de impacto con historial.
- Exponer metricas de duplicados historicos en `/api/impact-metrics`.
- Fortalecer monitoreo de scrapers.

### 12.2 Mediano plazo

- Medicion real de datos transferidos evitados.
- Estimacion mas rigurosa de energia y CO2.
- Dashboard historico por dia/semana/mes.
- Metricas por usuario suscrito.
- WhatsApp/Telegram en produccion.
- Alertas de cambios en selectores de medios.

### 12.3 Largo plazo

- Clustering semantico con embeddings.
- Deteccion por entidades, personas y lugares.
- Evaluacion de falsos positivos y falsos negativos.
- Modelos adaptados a noticias bolivianas.
- Panel para organizaciones, periodistas o analistas.

---

## 13. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Cambios en HTML de fuentes | Scraper puede extraer mal contenido | Tests por fuente, logs, selectores actualizados |
| Falsos positivos de deduplicacion | Se podria ocultar una noticia distinta | Umbral conservador, marcado sin borrar |
| Falsos negativos | Algunas repeticiones podrian pasar | Mejorar similitud y usar embeddings en roadmap |
| Costos IA al escalar | Incremento operativo | Cache, dedupe, ranking y modelos por tarea |
| Metricas ambientales inexactas | Riesgo de sobreprometer | Presentarlas como estimaciones transparentes |
| Mensajeria productiva | Costos y configuracion externa | Mantener demo web y preparar integracion gradual |

---

## 14. Por que puede ganar

EcoBrief Bolivia tiene una ventaja clara: convierte una aplicacion de IA en una solucion de sostenibilidad digital medible.

El proyecto no se limita a automatizar una tarea. Redisenia el flujo de consumo informativo para hacerlo mas eficiente:

- De muchas paginas a pocos briefs.
- De noticias repetidas a historias unicas.
- De IA aplicada sin filtro a IA aplicada despues de reducir ruido.
- De consumo pasivo a informacion personalizada.
- De impacto ambiguo a metricas visibles.

Ademas, el prototipo ya funciona. Esto permite demostrar el valor con una app real y no solo con una idea.

---

## 15. Conclusion

EcoBrief Bolivia demuestra que Green Tech tambien puede aplicarse al consumo de informacion. En un entorno digital saturado, el desperdicio no esta solo en servidores o energia: tambien esta en datos descargados sin necesidad, contenido duplicado, navegacion repetitiva y uso ineficiente de IA.

La propuesta usa IA de manera responsable para reducir ese desperdicio. Recolecta, limpia, deduplica, prioriza y resume solo lo necesario. El resultado es una experiencia informativa mas clara, eficiente y sostenible.

Mensaje final:

> EcoBrief Bolivia no crea mas ruido digital. Lo reduce.

