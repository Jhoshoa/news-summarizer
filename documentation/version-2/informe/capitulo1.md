# Capítulo 1 — Introducción

## 1.1 Contexto y motivación

En la era digital, el acceso a la información nunca ha sido tan amplio ni tan fragmentado. Para una persona en Bolivia, informarse sobre la actualidad nacional implica revisar múltiples medios de comunicación, abrir decenas de pestañas del navegador, comparar titulares, buscar contexto en redes sociales y descartar noticias repetidas. Este proceso, que parece cotidiano e inofensivo, genera un volumen significativo de desperdicio digital.

El **desperdicio digital informativo** se manifiesta de varias formas: tiempo perdido revisando la misma noticia en distintos sitios, datos móviles consumidos al cargar páginas completas con publicidad y *trackers*, procesamiento redundante cuando los sistemas de IA resumen artículos duplicados, y exposición a información fragmentada o sin fuente verificable en redes sociales.

Esta problemática se alinea directamente con los principios de **Green Tech**: promover un uso más eficiente, responsable y sostenible de la tecnología, la inteligencia artificial, el *cloud*, los datos y los procesos internos. No se trata solo de ahorrar tiempo, sino de repensar cómo consumimos y procesamos información digital.

## 1.2 El problema del desperdicio digital informativo

El desperdicio ocurre en cinco niveles interconectados:

| Nivel | Problema |
|---|---|
| Usuario | Tiempo perdido revisando noticias repetidas o poco relevantes |
| Datos | Carga innecesaria de páginas, imágenes, scripts y publicidad |
| IA | Procesamiento redundante si se resumen artículos duplicados o si un solo proveedor de IA colapsa toda la corrida |
| Ecosistema digital | Mayor navegación, más *requests* y más consumo de recursos |
| Confianza | Exposición a contenido viral, fragmentado o sin fuente trazable, y afirmaciones sin evidencia verificable |

Una misma noticia puede aparecer en varios medios con títulos distintos o URL diferentes. Sin una capa de deduplicación, agrupación de coberturas y trazabilidad, el usuario y el sistema terminan procesando información redundante o difícil de verificar. Esta versión del sistema agrega, respecto a la anterior, una capa explícita de **evidencia por afirmación** (*claims* con nivel de confianza y excerpt de origen), porque deduplicar no basta si el resumen resultante no puede respaldarse con la fuente original.

## 1.3 Objetivos

### Objetivo general

Desarrollar e implementar una plataforma de inteligencia artificial responsable que reduzca el desperdicio digital informativo mediante la recolección, deduplicación, agrupación de coberturas, clasificación, priorización y resumen trazable de noticias locales bolivianas.

### Objetivos específicos

1. Recolectar automáticamente noticias de las principales fuentes informativas de Bolivia mediante *web scraping*.
2. Implementar un sistema de deduplicación multinivel (URL, título, huella de contenido y agrupación de historias por ventana temporal) para eliminar redundancias entre corridas y entre fuentes.
3. Clasificar y priorizar noticias por categoría y relevancia para el contexto nacional, con un mecanismo explícito para detectar y corregir ambigüedad en las reglas de clasificación.
4. Generar resúmenes con IA aplicando criterios de eficiencia — filtrar, deduplicar, agrupar y rankear antes de enviar al modelo — y respaldar cada afirmación con evidencia trazable a un artículo fuente real.
5. Operar con resiliencia ante fallos de un proveedor de IA individual, mediante conmutación automática entre múltiples proveedores.
6. Medir y visualizar el impacto de la reducción del flujo informativo mediante métricas cuantificables extraídas de corridas reales.
7. Distribuir la información de forma personalizada según preferencias del usuario (categoría, canal, hora), reduciendo el consumo innecesario de datos.

## 1.4 Alcance y limitaciones

### Alcance

El proyecto abarca el desarrollo completo de una plataforma funcional que incluye:

- *Web scraping* de 6 medios de comunicación bolivianos activos hoy: Radio Fides, Unitel, Red Uno, Red Bolivisión, Los Tiempos y El Deber.
- Pipeline de procesamiento con deduplicación multinivel, agrupación de historias, clasificación con revisión asistida por IA, ranking y resumen con evidencia.
- Integración con 5 proveedores de IA (Groq, Gemini, GitHub Models, NVIDIA, OpenAI) mediante un enrutador con conmutación automática por fallas.
- Aplicación web con frontend React y backend FastAPI, incluyendo páginas nuevas de indicadores económicos y listado de fuentes.
- Base de datos PostgreSQL con esquema ampliado para historias, afirmaciones, evidencia y eventos de analítica.
- Sistema de suscripción con preferencias por categoría, canal y hora de entrega.
- Un módulo independiente de indicadores económicos (tipo de cambio oficial del BCB, cotizaciones Binance P2P).
- Un servicio de cron-job separado del backend, orquestando refrescos de indicadores, resúmenes y entregas.
- Panel de métricas de impacto Green Tech.
- Despliegue mediante Docker Compose (backend, frontend, cron-job y base de datos como contenedores independientes).

### Limitaciones

El sistema, aunque más maduro que en la versión 1, mantiene limitaciones identificadas honestamente:

- Las métricas de tiempo y MB siguen siendo estimaciones conservadoras, no mediciones energéticas directas.
- Los *scrapers* dependen de cambios en el HTML de los medios; dos de las ocho fuentes originales (Página Siete, ATB) fueron retiradas de la configuración activa y no se ha confirmado públicamente el motivo exacto de esa baja.
- La tabla de categorías en base de datos acumula filas históricas sin reglas de clasificación activas (variantes duplicadas o con problemas de codificación), producto de no tener una lista blanca a nivel de base de datos — un artículo mal etiquetado hoy sigue creando una categoría nueva "fantasma".
- `mypy` está configurado pero no se ejecuta en integración continua; el proyecto declara `pre-commit` como dependencia sin tener un archivo de configuración de hooks.
- La base de suscriptores activa es reducida (piloto cerrado), por lo que las métricas de entrega personalizada aún no reflejan un uso masivo.
- La detección de contradicciones entre fuentes fue evaluada y **deliberadamente omitida** del agrupador de historias por falta de una señal semántica confiable, y queda documentada como limitación conocida en el propio código.
