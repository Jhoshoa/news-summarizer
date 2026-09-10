# Resumen Ejecutivo

EcoBrief Bolivia es una plataforma que utiliza inteligencia artificial de forma responsable para reducir el desperdicio digital informativo. El sistema recolecta noticias de medios bolivianos, elimina duplicados, agrupa coberturas de una misma historia entre distintas fuentes, prioriza el contenido relevante y genera resúmenes con evidencia trazable, para que las personas no tengan que abrir múltiples páginas, leer la misma historia varias veces o consumir datos innecesarios.

Desde el informe de junio 2026 (versión 1), el sistema pasó de ser un MVP funcional a una plataforma con varias capas de robustez operativa que no existían antes:

- Deduplicación **multi-nivel real**: hash de URL, similitud de título, huella de contenido histórica, agrupación de historias por ventana temporal (*story clustering*) y una capa adicional de deduplicación **semántica con IA** antes de resumir.
- Clasificación de categorías con un **mecanismo anti-ambigüedad**: términos homónimos conocidos (p. ej. "selección", "mundial", "penal", "defensa") se marcan explícitamente y se priorizan para revisión por IA según un puntaje de riesgo, en vez de confiar ciegamente en coincidencias de palabras clave.
- Un **enrutador de proveedores de IA** con conmutación automática entre 5 proveedores (Groq, Gemini, GitHub Models, NVIDIA, OpenAI), en vez de una simple variable de entorno fija.
- Migración de **WhatsApp de Twilio a la API oficial de Meta**, eliminando un intermediario de costo y dependencia.
- Un módulo nuevo de **indicadores económicos** (tipo de cambio oficial del BCB, cotizaciones Binance P2P) que no existía en la versión anterior.
- Un servicio de **cron-job independiente**, containerizado y separado del backend, que orquesta las corridas del pipeline, los resúmenes y la entrega a suscriptores.

La propuesta central no cambió: no busca crear más contenido, busca reducir el ruido digital.

- De muchas páginas a pocos resúmenes.
- De noticias repetidas a historias únicas, con evidencia y nivel de confianza por afirmación.
- De navegación manual a información personalizada por canal y hora preferida.
- De IA aplicada sin filtro a IA aplicada después de deduplicar, agrupar y priorizar.
- De impacto ambiguo a métricas medidas en cada corrida real del sistema.

En la última corrida completa con datos íntegros (7 de septiembre de 2026), el sistema recolectó 115 artículos y produjo 52 resúmenes, una reducción del 54.8 % del flujo informativo — con datos reales del sistema en producción, no una simulación.

> **Mensaje central:** EcoBrief Bolivia usa IA no para producir más ruido, sino para reducirlo — y cada capa nueva que se agregó desde la v1 (dedup. semántica, story clustering, fallback multi-proveedor) fue una respuesta a un problema real observado en producción, no una funcionalidad especulativa.
