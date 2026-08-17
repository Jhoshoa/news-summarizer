# EcoBrief Bolivia - Estado actual, hallazgos y roadmap

Fecha de relevamiento: 2026-08-17

Este documento resume el estado tecnico actual del proyecto, los problemas encontrados durante
la revision local con Docker, y una propuesta de trabajo incremental para mejorar calidad,
operacion local, despliegue en VPS/Dokploy y confiabilidad del pipeline.

## 1. Contexto del proyecto

EcoBrief Bolivia es una aplicacion para recolectar noticias bolivianas, procesarlas,
resumirlas con modelos LLM, almacenarlas y distribuir briefs por canales como email,
Telegram o WhatsApp.

La aplicacion combina:

- Backend FastAPI.
- Frontend React/Vite.
- Base de datos PostgreSQL.
- Cron job separado para tareas programadas.
- Scrapers de medios bolivianos.
- NewsAPI como fuente complementaria.
- Procesadores para filtrado, deduplicacion, clasificacion, ranking, resumen y reescritura.
- Documentacion tecnica y narrativa en `documentation/version-1` y `docs/`.

## 2. Estructura actual del repositorio

### Backend

Codigo principal:

```text
src/
```

Entrada de la API:

```text
src/main.py
```

Modulos principales:

- `src/collectors/`: recolectores de noticias, incluyendo scraping y NewsAPI.
- `src/processors/`: deduplicacion, clasificacion, ranking, resumen y reescritura.
- `src/llm/`: proveedores LLM y failover.
- `src/db/`: modelos, conexion y persistencia.
- `src/distributors/`: canales de entrega como WhatsApp, Telegram y email.
- `src/scheduler/`: scheduler interno legacy.
- `src/api/`: routers auxiliares.
- `src/config/`: carga de settings desde variables de entorno.

### Frontend

Codigo principal:

```text
frontend/
```

Stack:

- React.
- Vite.
- Redux Toolkit Query.

El frontend consume endpoints del backend usando:

```text
VITE_API_BASE_URL
```

Nota importante: al ser Vite, las variables `VITE_*` quedan embebidas durante el build.
Cambiar `VITE_API_BASE_URL` en produccion requiere reconstruir la imagen del frontend.

### Cron job

Codigo principal:

```text
cron-job/
```

El cron se ejecuta como un contenedor independiente y llama al backend por HTTP.
Dentro de Docker Compose debe usar la red interna:

```text
http://backend:8000
```

### Docker

Archivos principales despues de la mejora de configuracion:

- `docker-compose.yml`: base orientada a produccion y Dokploy.
- `docker-compose.local.yml`: overrides explicitos para desarrollo local.
- `Dockerfile.backend`: build del backend.
- `frontend/Dockerfile`: build del frontend.
- `cron-job/Dockerfile`: build del cron job.

### Configuracion de fuentes

Las fuentes de scraping viven en:

```text
config/sources.yaml
```

## 3. Flujo funcional esperado

El flujo esperado de generacion de resumen es:

1. Revisar si hay summaries cacheados para la fecha.
2. Revisar si hay articulos recientes cacheados.
3. Si el cache no alcanza, recolectar desde scrapers y NewsAPI.
4. Filtrar articulos inutilizables o antiguos.
5. Guardar/upsert de articulos en PostgreSQL.
6. Deduplicar por URL y titulos similares.
7. Clasificar por categoria.
8. Rankear por relevancia, recencia, fuente y calidad.
9. Seleccionar candidatos por categoria.
10. Resumir con LLM.
11. Reescribir summaries para estilo consistente.
12. Guardar summaries.
13. Entregar briefs desde `/trigger/delivery` cuando hay suscriptores activos.

Separacion importante de endpoints:

- `/trigger/summary`: genera o refresca contenido.
- `/trigger/delivery`: entrega summaries ya guardados a suscriptores.

## 4. Estado validado localmente

Se levanto el stack Docker completo:

- `postgres`
- `backend`
- `frontend`
- `cron-job`

Validaciones realizadas:

- Backend `/health`: healthy.
- Base de datos: connected.
- Frontend: responde HTTP 200 en `http://localhost:5173`.
- CORS local: permite `http://localhost:5173`.
- Cron job: corre dentro de Docker y llama al backend.
- `/api/articles`: devuelve articulos.
- `/api/summaries`: devuelve summaries cuando hay LLM configurado.
- `/api/impact-metrics`: devuelve metricas del pipeline.

Tambien se confirmo que el pipeline ejecuta:

- Scraping.
- Filtro de articulos inutilizables.
- Filtro de antiguedad.
- Deduplicacion.
- Upsert en base de datos.
- Ranking.
- Generacion de summaries cuando hay API key LLM disponible.

## 5. Problemas encontrados

### 5.1 Variables de entorno no llegaban al backend Docker

Sintoma:

```text
collected > 0
summaries = 0
```

Y en logs:

```text
No hay LLM para resumir
```

Causa:

El contenedor del backend no recibia variables como:

- `GROQ_API_KEY`
- `NEWS_API_KEY`
- `SCRAPER_*`
- `EMAIL_*`
- `TELEGRAM_*`
- `TWILIO_*`

Resultado:

El backend podia recolectar datos, pero no podia invocar el proveedor LLM.

Estado:

Corregido en `docker-compose.yml`.

### 5.2 CORS mezclaba local y produccion

Sintoma:

El frontend local podia fallar aunque el backend respondiera desde terminal.

Causa:

`CORS_ORIGINS` estaba hardcodeado con dominios/IPs de produccion y no siempre incluia:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Estado:

Corregido separando:

- Produccion: `docker-compose.yml`
- Local: `docker-compose.local.yml`

### 5.3 API key de endpoints internos en Docker podia quedar stale

Sintoma:

Llamadas con `X-API-Key` devolvian:

```json
{
  "detail": "API key invalida"
}
```

Causa:

Docker Compose habia creado el contenedor con una version anterior de `API_AUTH_KEY`.
Un `restart` no actualiza variables de entorno; hay que recrear el contenedor.

Solucion:

```powershell
docker compose up -d --force-recreate backend cron-job
```

Estado:

Resuelto durante la revision.

### 5.4 `VITE_API_BASE_URL` es build-time

Riesgo:

En produccion, si `VITE_API_BASE_URL` queda como:

```text
http://localhost:8000
```

el navegador del usuario intentara llamar a su propia maquina, no al VPS.

Estado:

Documentado en `DEPLOYMENT.md` y `.env.prod.example`.

### 5.5 Parser del LLM es fragil

Sintoma observado:

Algunas categorias fallaban con:

```text
LLM response did not include a JSON array
```

Impacto:

Una corrida puede generar summaries para algunas categorias y `0` summaries para otras,
aunque existan candidatos validos.

Riesgo:

La calidad final del brief depende demasiado de que el modelo devuelva JSON perfecto.

Pendiente:

Implementar parsing robusto, validacion de schema y fallback.

### 5.6 Drift de categorias generado por LLM

Sintoma:

Se observaron categorias fuera del set esperado, por ejemplo:

```text
clima
cultura
```

Categorias esperadas:

```text
economia
politica
deportes
tecnologia
entretenimiento
policiales
general
```

Impacto:

- Frontend puede filtrar mal.
- Metricas por categoria pueden quedar inconsistentes.
- Delivery por preferencias puede enviar contenido incorrecto.

Pendiente:

Normalizar categorias despues del LLM y antes de persistir.

### 5.7 Timeout del endpoint manual

Sintoma:

La llamada a `/trigger/summary` puede tardar varios minutos. El cliente puede hacer timeout
aunque el backend siga procesando y termine correctamente.

Impacto:

- Mala experiencia en frontend.
- Dificil saber si el proceso fallo o sigue corriendo.
- Riesgo en proxies o plataformas con timeouts estrictos.

Pendiente:

Convertir el refresh manual en job asincrono con endpoint de estado, o reducir tiempo de
procesamiento.

### 5.8 CI/CD no esta versionado

Hallazgo:

No se encontro `.github/` con GitHub Actions.

Pendiente:

Agregar CI minimo con:

- Backend tests.
- Ruff.
- Frontend lint/build.
- Docker Compose config validation.

### 5.9 Migraciones de base de datos poco formales

Hallazgo:

Hay migraciones SQL sueltas y archivos con numeracion duplicada.

Pendiente:

Definir un flujo formal:

- Alembic, o
- runner propio de migraciones, o
- documentacion operacional estricta para SQL manual.

### 5.10 README y documentacion no estaban alineados

Hallazgos:

- README tenia informacion vieja.
- Decia que no habia tests, pero se habian validado tests existentes.
- Describia `/trigger/summary` como si tambien hiciera delivery.
- Faltaba explicar local vs produccion/Dokploy.

Estado:

Parte inicial corregida con `DEPLOYMENT.md`, `.env.local.example`, `.env.prod.example` y README.

## 6. Cambios recientes ya aplicados

### 6.1 Separacion Docker local/produccion

Se definio:

```text
docker-compose.yml         # produccion / Dokploy
docker-compose.local.yml   # desarrollo local
```

Motivo:

Evitar que produccion herede valores locales como `localhost`.

### 6.2 Plantillas de entorno

Se agrego:

```text
.env.local.example
.env.prod.example
```

Y `.env.example` quedo como guia corta.

### 6.3 Documentacion de despliegue

Se agrego:

```text
DEPLOYMENT.md
```

Incluye:

- Comando local.
- Compose Path para Dokploy.
- Variables criticas de produccion.
- Regla sobre `VITE_API_BASE_URL`.

## 7. Como correr localmente

Preparar `.env`:

```powershell
copy .env.local.example .env
```

Editar `.env` y configurar al menos una key LLM:

```env
GROQ_API_KEY=...
```

Levantar stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

Verificar:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -UseBasicParsing
```

Frontend:

```text
http://localhost:5173
```

## 8. Como desplegar en Dokploy

En Dokploy:

```text
Compose Path: ./docker-compose.yml
```

No usar:

```text
docker-compose.local.yml
```

Variables base para Dokploy:

```env
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://ecobriefbolivia.online,https://briefs.ecobriefbolivia.online
VITE_API_BASE_URL=https://ecobriefbolivia.online
GROQ_API_KEY=...
NEWS_API_KEY=...
API_AUTH_KEY=...
POSTGRES_PASSWORD=...
```

Si el backend se publica en subdominio separado:

```env
VITE_API_BASE_URL=https://api.ecobriefbolivia.online
CORS_ORIGINS=https://ecobriefbolivia.online,https://briefs.ecobriefbolivia.online
```

## 9. Roadmap recomendado

### Paso 1 - Robustecer parser LLM y normalizacion de categorias

Objetivo:

Reducir summaries perdidos por respuestas no perfectas del modelo.

Trabajo:

- Extraer JSON aunque venga dentro de texto o markdown.
- Validar que el resultado sea lista.
- Validar campos obligatorios.
- Normalizar categorias a un set permitido.
- Preservar categoria original si aporta valor para debug.
- Agregar tests unitarios.

Resultado esperado:

- Menos categorias con `0` summaries por fallas de formato.
- Datos mas consistentes en frontend, DB y delivery.

### Paso 2 - Revisar frontend y estados de datos

Objetivo:

Que el frontend muestre informacion de forma clara cuando hay summaries, articulos, cache,
fallback a ultimo dia o errores.

Trabajo:

- Revisar consumo de `/api/summaries`.
- Revisar consumo de `/api/articles`.
- Revisar filtros por fecha/categoria.
- Mejorar estados vacios y de error.
- Confirmar que `fallback_to_latest` sea visible o predecible.

### Paso 3 - Corregir Ruff

Objetivo:

Dejar lint minimo en verde.

Trabajo:

- Corregir `B904` en `src/api/worldcup.py`.
- Correr `ruff check src tests`.

### Paso 4 - CI basico

Objetivo:

Evitar regressions antes de deployar.

Trabajo:

- Agregar GitHub Actions.
- Validar backend tests.
- Validar ruff.
- Validar frontend install/lint/build.
- Validar `docker compose config`.

### Paso 5 - Migraciones DB

Objetivo:

Hacer mas seguro el despliegue de cambios de schema.

Trabajo:

- Revisar `migrations/`.
- Resolver numeracion duplicada.
- Decidir Alembic vs runner SQL.
- Documentar flujo de upgrade.

### Paso 6 - Endpoint asincrono para refresh manual

Objetivo:

Evitar timeouts de `/trigger/summary`.

Trabajo:

- Crear job id para refresh.
- Endpoint para consultar estado.
- Mostrar estado en frontend si se habilita refresh manual.
- Mantener cron compatible.

### Paso 7 - Uniformar documentacion

Objetivo:

Alinear README, docs tecnicos y documentacion de concurso con la realidad del sistema.

Trabajo:

- Revisar `documentation/version-1`.
- Revisar LaTeX de concurso.
- Revisar diagramas PlantUML.
- Actualizar arquitectura real.
- Documentar limitaciones actuales y roadmap.

## 10. Estrategia de commits recomendada

Para mantener historial claro:

1. Commit de configuracion Docker/local/prod.
2. Commit de este documento de relevamiento.
3. Commit de parser LLM robusto y tests.
4. Commit de normalizacion de categorias si queda grande y conviene separarlo.
5. Commit de frontend states/fallback.
6. Commit de ruff.
7. Commit de CI.
8. Commit de migraciones/documentacion DB.
9. Commit de refresh async.
10. Commit de uniformacion de documentacion larga.

## 11. Prioridad inmediata

La siguiente implementacion recomendada es:

```text
Robustecer parser LLM y normalizar categorias antes de persistir summaries.
```

Motivo:

Es el problema que afecta directamente la calidad del producto: si el modelo responde en un
formato levemente distinto, se pierden summaries completos por categoria. Tambien es una mejora
relativamente contenida, testeable y de bajo riesgo si se cubre con tests unitarios.
