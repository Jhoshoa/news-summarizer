# Capítulo 7 — Estado Actual y Roadmap

Este capítulo ya no es una lista de entregables para una fecha de concurso: es la hoja de ruta de un producto en desarrollo continuo, con features en distintas etapas de madurez — algunas ya en producción, otras en progreso, otras todavía en evaluación. La pregunta que guía esta sección no es "¿cumplimos los requisitos?", sino "¿qué necesita este producto para seguir mejorando?".

## 7.1 MVP funcional — qué se agregó desde la versión 1

El MVP descrito en junio de 2026 ya funcionaba. Lo que cambió es la profundidad de varias de sus piezas:

- **Deduplicación multinivel real**, incluyendo agrupación de historias por ventana temporal y una capa de verificación semántica con IA — la versión anterior describía 3 niveles; hoy son 4, cada uno resolviendo un problema distinto detectado en producción.
- **Clasificación con mecanismo anti-ambigüedad**: amortiguador de término dominante, marcado explícito de términos homónimos y priorización de revisión por IA según puntaje de riesgo.
- **Enrutador multi-proveedor de IA** (5 proveedores con conmutación automática), en vez de un proveedor fijo por variable de entorno.
- **WhatsApp migrado a la API oficial de Meta**, eliminando la dependencia de Twilio.
- **Telegram migrado de *polling* a webhook**.
- **Generación de resúmenes asíncrona** con sondeo de estado, en vez de una llamada bloqueante — necesario tras observar corridas reales de más de 9 minutos.
- **Módulo nuevo de indicadores económicos** (dólar oficial BCB, Binance P2P), incluyendo sus propias páginas de frontend (Datos, Fuentes).
- **cron-job como servicio independiente**, separado del backend, con su propio ciclo de vida.
- **Esquema de base de datos ampliado** con historias, afirmaciones, evidencia, eventos de analítica y trabajos asíncronos — 17 migraciones incrementales aplicadas.
- **CI con 3 verificaciones** (backend: ruff + pytest; frontend: tests de rutas + eslint + build; validación de configuración Docker Compose para producción y local) y 45 archivos de test.

## 7.2 Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, gunicorn + uvicorn workers |
| Frontend | React 19, Vite 6, TypeScript 5.7 |
| Base de datos | PostgreSQL 15, SQLAlchemy (async), 17 migraciones SQL versionadas |
| *Web scraping* | httpx, BeautifulSoup4, lxml |
| IA | Groq, Gemini, GitHub Models, NVIDIA, OpenAI (enrutados con failover) |
| Infraestructura | Docker Compose (4 servicios: postgres, backend, frontend, cron-job) |
| Distribución | Telegram Bot API (webhook), WhatsApp Cloud API (Meta directo), SMTP |
| Linting | Ruff (en CI) |
| Tipado | mypy (configurado, **no** corre en CI) |
| Pruebas | pytest, pytest-asyncio, pytest-cov — 45 archivos de test |
| CI/CD | GitHub Actions (3 jobs) |
| Control de versiones | Git, GitHub |

## 7.3 En progreso y próximas features

### En progreso ahora

Deuda técnica y ajustes ya identificados, con trabajo activo o inminente:

- Ejecutar `mypy` en CI — está configurado como dependencia y en `pyproject.toml`, pero el workflow actual no lo invoca.
- Agregar el archivo de configuración de `pre-commit` — la dependencia ya está declarada, falta el `.pre-commit-config.yaml`.
- Limpiar las filas históricas sin reglas activas en `news_categories` (duplicados de "entretenimiento", una fila con codificación rota, y "no es politica"), y agregar una lista blanca a nivel de base de datos para que un valor de categoría inválido no cree una fila permanente nunca más.
- Limpiar los pesos de fuente obsoletos (`la_razon`, `opinion`) en `config/scoring.yaml`, que ya no tienen fuente correspondiente activa.
- Evaluar si conviene reincorporar Página Siete y/o ATB a `config/sources.yaml`, o documentar formalmente el motivo de su baja.

### Próximas features (mediano plazo)

Funcionalidades planificadas para hacer crecer el producto más allá del piloto actual:

- Monitorear la tasa de corroboración entre fuentes (`source_article_count` promedio) durante varias semanas para evaluar si el umbral de similitud de historias (0.85) es demasiado conservador con solo 6 fuentes activas.
- Ampliar la base de suscriptores activos más allá del piloto cerrado actual, y usar datos reales de entrega (no solo de generación) para refinar las métricas de impacto.
- Medir datos reales descargados y evitados (no solo estimaciones), aprovechando que ya existe telemetría de eventos de uso (`analytics_events`).
- Evaluar la detección de contradicciones entre fuentes con una señal semántica más confiable que la descartada en la iteración actual.

### Visión a futuro (largo plazo)

Ideas de mayor alcance, sin compromiso de fecha — se evalúan a medida que el producto y su base de usuarios crecen:

- Detección por entidades, personas y lugares sobre las historias ya agrupadas.
- Planes de suscripción para usuarios avanzados, organizaciones y analistas.
- Panel institucional para monitoreo de noticias, comunicados y alertas públicas.
- Monitoreo automático de cambios estructurales en las fuentes de scraping, para detectar selectores rotos antes de que dejen de recolectar silenciosamente.
- Evaluar programas de aceleración para startups (Y Combinator u otros) una vez exista tracción real que lo respalde. Con el piloto actual (un puñado de suscriptores), convertir esto en un objetivo formal del proyecto sería prematuro — queda anotado como posibilidad a revisar más adelante, no como plan.

## 7.4 Riesgos técnicos y mitigación

| Riesgo | Mitigación |
|---|---|
| Cambios de HTML en fuentes | Selectores configurables por fuente y *fallback* genérico de extracción de enlaces |
| Falsos positivos en clasificación por homónimos | Amortiguador de término dominante, marcado `ambiguous` y revisión priorizada por IA — proceso vivo, se agregan casos según se detectan |
| Falla o degradación de un proveedor de IA | Enrutador con conmutación automática entre 5 proveedores y *timeouts* agresivos |
| Corridas de resumen más largas de lo esperado | Ejecución asíncrona con sondeo de estado en vez de llamada bloqueante |
| Datos de terceros incorrectos o desactualizados (indicadores económicos) | Verificación contra la fuente original y pruebas de regresión — ver los dos casos reales corregidos esta semana (Capítulo 3.7) |
| Categorías o configuraciones obsoletas acumulándose silenciosamente | Identificado en esta revisión (categorías legacy, fuentes de scoring obsoletas); pendiente de limpieza activa |
| Cobertura de tipos sin verificar en CI | `mypy` configurado pero no ejecutado — riesgo de que errores de tipo lleguen a producción sin ser detectados |
