# EcoBrief Bolivia

## IA responsable para reducir desperdicio digital informativo

**Equipo:** Josoe Ichuta, Ingenieria; Raquel Auza, Digital-Academy  
**Propuesta:** Green Tech aplicada al consumo eficiente de informacion local  
**Estado:** prototipo funcional

---

## 1. Resumen ejecutivo

EcoBrief Bolivia es una plataforma que usa IA de forma responsable para reducir desperdicio digital informativo. El sistema recopila noticias locales, elimina duplicados, prioriza lo relevante y genera briefs claros para que las personas no tengan que abrir multiples paginas, leer la misma historia varias veces o consumir datos innecesarios.

La propuesta no busca crear mas contenido. Busca reducir ruido digital.

EcoBrief transforma un flujo disperso de noticias en informacion breve, priorizada y medible:

- De muchas paginas a pocos briefs.
- De noticias repetidas a historias unicas.
- De IA aplicada sin filtro a IA aplicada despues de deduplicar.
- De navegacion manual a informacion personalizada.
- De impacto ambiguo a metricas visibles.

El prototipo ya cuenta con scraping real de medios locales, clasificacion por categorias, ranking de prioridad, resumenes con IA, deduplicacion historica, base de datos, frontend y pagina de impacto.

Mensaje central:

> EcoBrief Bolivia usa IA no para producir mas ruido, sino para reducirlo.

---

## 2. Problema Green Tech

Informarse sobre la actualidad boliviana suele implicar revisar varios medios, abrir muchas paginas, comparar titulares y descartar noticias repetidas. Este proceso genera desperdicio digital.

El desperdicio ocurre en cuatro niveles:

| Nivel | Problema |
|---|---|
| Usuario | Tiempo perdido revisando noticias repetidas o poco relevantes |
| Datos | Carga innecesaria de paginas, imagenes, scripts y publicidad |
| IA | Procesamiento redundante si se resumen articulos duplicados |
| Ecosistema digital | Mayor navegacion, mas requests y mas consumo de recursos |

Una misma noticia puede aparecer en varios medios, con titulos distintos o URLs diferentes. Sin una capa de deduplicacion y priorizacion, el usuario y el sistema terminan procesando informacion redundante.

---

## 3. Solucion EcoBrief

EcoBrief Bolivia actua como una capa de eficiencia entre las fuentes de noticias y las personas.

El sistema:

1. Recolecta noticias de medios bolivianos.
2. Extrae contenido util: titulo, descripcion, cuerpo, imagen, fecha y fuente.
3. Descarta articulos sin contenido suficiente.
4. Detecta duplicados por URL, titulo y huella de historia.
5. Clasifica por categoria.
6. Prioriza por relevancia.
7. Resume con IA solo los articulos seleccionados.
8. Presenta una experiencia web clara.
9. Prepara distribucion personalizada por preferencias.
10. Mide impacto digital estimado.

**Diagrama recomendado:** ver `diagrams/executive-flow.puml`.

---

## 4. Antes vs despues

| Antes | Con EcoBrief |
|---|---|
| Abrir varios sitios de noticias | Ver un brief centralizado |
| Leer titulares repetidos | Ver historias deduplicadas |
| Consumir paginas completas | Consumir resumenes compactos |
| Procesar todo con IA | Usar IA solo despues de filtrar y priorizar |
| No saber cuanto se reduce | Ver metricas de impacto |
| Recibir informacion no personalizada | Elegir categorias y frecuencia |

La mejora no es solo de productividad. Es eficiencia digital: menos operaciones innecesarias para llegar a informacion util.

---

## 5. Por que es Green Tech

EcoBrief Bolivia encaja en Green Tech porque promueve un uso mas eficiente y responsable de software, datos e IA.

### 5.1 Reduce navegacion innecesaria

El usuario no necesita abrir multiples paginas para entender los hechos principales. El sistema entrega una sintesis priorizada.

### 5.2 Reduce duplicacion informativa

La deduplicacion evita que la misma historia sea procesada y mostrada varias veces.

### 5.3 Reduce llamadas IA redundantes

La IA se usa despues de limpiar, filtrar, deduplicar y rankear. Esto evita enviar contenido irrelevante o repetido al modelo.

### 5.4 Reduce consumo de datos

El usuario puede leer briefs compactos en lugar de cargar paginas completas con imagenes, publicidad, trackers y scripts.

### 5.5 Promueve consumo digital responsable

Las preferencias por categoria y frecuencia reducen informacion no solicitada y evitan spam informativo.

---

## 6. Impacto medible

EcoBrief mide impacto a partir del flujo real del sistema. Las metricas ambientales son estimaciones transparentes, no mediciones energeticas directas.

### 6.1 Metricas reales

El sistema puede reportar:

- Articulos recolectados.
- Articulos utiles.
- Duplicados detectados.
- Articulos unicos.
- Articulos enviados a ranking.
- Candidatos enviados a IA.
- Briefs generados.
- Cache reutilizado.
- Duplicados historicos detectados.

### 6.2 Metricas estimadas

Con base en el flujo anterior, se estiman:

- Paginas evitadas.
- Minutos ahorrados.
- MB no descargados.
- Llamadas IA evitadas.
- Tasa de reduccion del flujo.

Formulas:

```text
paginas_evitadas = articulos_recolectados - briefs_generados
minutos_ahorrados = paginas_evitadas * 0.5
mb_ahorrados = paginas_evitadas * 0.8
tasa_reduccion = 1 - (briefs_generados / articulos_recolectados)
```

Estos supuestos son conservadores y pueden reemplazarse por mediciones reales en una siguiente etapa.

### 6.3 Ejemplo de tabla para completar con datos de demo

| Metrica | Valor demo |
|---|---:|
| Noticias recolectadas | Completar con corrida real |
| Articulos utiles | Completar con corrida real |
| Duplicados eliminados | Completar con corrida real |
| Candidatos a IA | Completar con corrida real |
| Briefs generados | Completar con corrida real |
| Paginas evitadas | Completar con corrida real |
| Minutos ahorrados | Completar con corrida real |
| MB estimados ahorrados | Completar con corrida real |
| Tasa de reduccion | Completar con corrida real |

**Diagrama recomendado:** ver `diagrams/impact-funnel.puml`.

---

## 7. Estado actual del prototipo

EcoBrief Bolivia no es solo una idea. El prototipo ya funciona.

### 7.1 Funcionalidades implementadas

- Scraping de noticias locales.
- Extraccion de contenido desde paginas reales.
- Correccion de selectores cuando cambia el HTML de una fuente.
- Clasificacion por categorias.
- Ranking por relevancia.
- Deduplicacion por URL y titulo.
- Deduplicacion historica por huella de historia.
- Resumenes generados con IA.
- Persistencia en PostgreSQL.
- Frontend con paginas Home, Noticias, Detalle, Impacto y Suscripcion.
- Preferencias por categoria y frecuencia.
- Endpoint manual para generar summaries.
- Base para distribucion por WhatsApp y Telegram.

### 7.2 Evidencia de madurez

El sistema tiene tests automatizados, migraciones de base de datos, arquitectura modular y metricas del pipeline. Esto permite demostrar la solucion con una app real y no solo con mockups.

---

## 8. Costos

EcoBrief fue disenado para operar con bajo costo y con una infraestructura simple: un solo VPS para backend, frontend, base de datos y cron-jobs.

### 8.1 Infraestructura propuesta para 1 ano

| Componente | Proveedor / plan | Uso en EcoBrief | Costo de referencia |
|---|---|---|---:|
| Servidor VPS | Hostinger KVM 2 | Backend, frontend, PostgreSQL, cron-jobs y servicios internos | USD 8.99/mes; USD 107.88/ano referencial |
| Dominio | NIC Bolivia | Dominio `.bo` del proyecto | 55 Bs/ano |
| Base de datos | PostgreSQL en el VPS | Persistencia de noticias, summaries, usuarios y metricas | Incluido en VPS |
| Backend | FastAPI en el VPS | API, scraping, pipeline, IA y metricas | Incluido en VPS |
| Frontend | React/Vite servido desde el VPS | Interfaz web publica | Incluido en VPS |
| Cron-jobs | Scheduler en el VPS | Ejecucion programada de recoleccion y resumenes | Incluido en VPS |
| Email / SMTP | Gmail SMTP con Google App Password | Notificaciones, validaciones o envio de correos | Gratuito dentro de los limites de envio de Google; luego migrable a Brevo u otro SMTP |
| Telegram | Bot API | Canal de distribucion de briefs | Gratuito |
| WhatsApp | Twilio WhatsApp Business | Canal opcional de mensajeria | Variable por conversacion/mensaje; Bolivia referencial desde USD 0.0116 outbound/minuto segun tabla Twilio |
| IA actual | Groq API | Resumen, clasificacion y reescritura durante prototipo | Free tier para demo; costo bajo si escala |

Nota: los precios externos pueden cambiar. Para la entrega se presentan como referencias operativas, no como cotizacion contractual.

### 8.2 Modelos IA usados actualmente

El prototipo usa Groq como proveedor principal por velocidad y bajo costo de entrada.

Modelos configurados:

| Tarea | Modelo actual | Uso |
|---|---|---|
| Resumen de mayor calidad | `llama-3.3-70b-versatile` | Generar summaries finales |
| Tareas rapidas | `llama-3.1-8b-instant` | Clasificacion o tareas livianas |
| Balanceado / reescritura | `llama-3.1-70b-versatile` | Normalizacion de estilo cuando aplica |

Precios Groq de referencia:

| Modelo | Input / 1M tokens | Output / 1M tokens |
|---|---:|---:|
| Llama 3.3 70B Versatile | USD 0.59 | USD 0.79 |
| Llama 3.1 8B Instant | USD 0.05 | USD 0.08 |

En la demo se usa el free tier de Groq; en produccion se mantiene la misma arquitectura y se paga por consumo si el volumen supera el nivel gratuito.

### 8.3 Comparativa referencial de proveedores IA

La arquitectura permite cambiar de proveedor porque el cliente LLM esta abstraido. Esta tabla muestra alternativas para estimar costos futuros.

| Proveedor | Modelo referencial | Input / 1M tokens | Output / 1M tokens | Comentario |
|---|---|---:|---:|---|
| Groq | Llama 3.3 70B Versatile | USD 0.59 | USD 0.79 | Opcion actual; rapida y barata |
| OpenAI | GPT-5.4 mini | USD 0.75 | USD 4.50 | Opcion economica dentro de OpenAI |
| OpenAI | GPT-5.4 | USD 2.50 | USD 15.00 | Mayor capacidad, mayor costo |
| DeepSeek | DeepSeek V4 Flash | USD 0.14 cache miss; USD 0.0028 cache hit | USD 0.28 | Muy competitivo en costo |
| DeepSeek | DeepSeek V4 Pro | USD 0.435 cache miss; USD 0.003625 cache hit | USD 0.87 | Mayor costo que Flash, aun competitivo |
| Anthropic | Claude Haiku 4.5 | USD 1.00 | USD 5.00 | Opcion eficiente dentro de Claude |
| Anthropic | Claude Sonnet 4.6 | USD 3.00 | USD 15.00 | Mayor calidad/costo para casos complejos |

Conclusion de costos IA: EcoBrief debe mantener Groq o DeepSeek para volumen operativo y reservar modelos mas costosos solo para tareas donde la calidad lo justifique.

### 8.4 Control de costos

La arquitectura reduce costos porque:

- No resume todo lo recolectado.
- Deduplica antes de IA.
- Cachea resultados.
- Limita candidatos por categoria.
- Permite usar modelos pequenos para tareas simples.
- Personaliza contenido por usuario.
- Usa Telegram como canal gratuito.
- Deja WhatsApp como canal opcional cuando exista presupuesto.

Formula de referencia:

```text
costo_ia = llamadas_ia * costo_promedio_por_llamada
ahorro_ia = llamadas_evitas * costo_promedio_por_llamada
```

### 8.5 Escenario operativo recomendado

Para el concurso y un primer despliegue publico, la estrategia recomendada es:

1. Desplegar todo en Hostinger KVM 2 por 1 ano.
2. Usar dominio comprado en NIC Bolivia.
3. Usar Groq free tier o pago bajo para IA.
4. Usar Telegram y Gmail SMTP con App Password como canales de bajo costo.
5. Activar WhatsApp/Twilio como opcion futura o piloto controlado.
6. Medir llamadas IA, usuarios y volumen antes de escalar.

Con este enfoque, el MVP puede operar con un costo fijo anual bajo y costos variables controlados.

### 8.6 Fuentes de referencia de precios

- Hostinger VPS KVM 2: https://www.hostinger.com/vps-hosting
- NIC Bolivia: costo indicado para dominio `.bolivia.bo`: 55 Bs/año.
- Google App Passwords: https://support.google.com/accounts/answer/185833
- Limites de envio Gmail/Google Workspace: https://support.google.com/a/answer/166852
- Twilio WhatsApp: https://www.twilio.com/en-us/whatsapp/pricing
- Groq pricing: https://groq.com/pricing/
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
- Anthropic Claude pricing: https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI pricing: https://openai.com/api/pricing/

---

## 9. Demo recomendada

Para una presentacion o video de 2 a 3 minutos:

1. Mostrar el problema: muchas noticias, duplicacion y ruido.
2. Abrir Home y mostrar noticias priorizadas.
3. Abrir una noticia con cuerpo y fuente original.
4. Mostrar pagina de Noticias.
5. Ejecutar resumen manual.
6. Mostrar pagina de Impacto.
7. Mostrar preferencias de suscripcion.
8. Cerrar con el mensaje Green Tech.

Frase de cierre:

> EcoBrief reduce paginas, duplicados y llamadas IA innecesarias para entregar informacion local esencial.

---

## 10. Limitaciones y honestidad tecnica

El prototipo tiene limitaciones claras:

- Las metricas de tiempo y MB son estimaciones, no mediciones energeticas directas.
- Los scrapers dependen de cambios en HTML de los medios.
- WhatsApp en produccion requiere credenciales y costos externos.
- No todos los articulos historicos tienen backfill de huellas.
- La agrupacion semantica avanzada con embeddings esta en roadmap.
- La estimacion de CO2 requiere una metodologia mas rigurosa.

Estas limitaciones estan identificadas y no afectan la demostracion del MVP.

---

## 11. Roadmap

### Corto plazo

- Completar backfill de fingerprints historicos.
- Mostrar en UI cuantas coberturas fueron agrupadas.
- Exponer duplicados historicos en pagina de impacto.
- Mejorar historial de metricas.

### Mediano plazo

- Medir datos reales descargados/evitados.
- Agregar estimacion de energia y CO2 con metodologia documentada.
- Activar WhatsApp/Telegram en produccion.
- Crear dashboard por usuario.

### Largo plazo

- Clustering semantico con embeddings.
- Deteccion por entidades, personas y lugares.
- Panel para organizaciones, periodistas o analistas.
- Monitoreo automatico de cambios en fuentes.

---

## 12. Por que deberia ganar

EcoBrief Bolivia convierte un problema cotidiano en una solucion Green Tech concreta: reduce desperdicio digital informativo usando IA de forma responsable.

El proyecto tiene tres fortalezas para el concurso:

1. **Alineacion clara:** reduce navegacion, duplicacion, datos y procesamiento IA innecesario.
2. **Prototipo funcional:** no es solo una idea; ya existe una app con backend, frontend, BD y metricas.
3. **Impacto medible:** el sistema muestra reduccion del flujo informativo y permite estimar ahorro de tiempo, paginas y datos.

Mensaje final:

> EcoBrief Bolivia demuestra que la IA puede ser mas sostenible cuando se usa para reducir, no para multiplicar, el contenido digital.
