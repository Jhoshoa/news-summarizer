# Alinear el sistema de categorias en toda la aplicacion

> **Estado: Fases 1-4 implementadas.** Ver commits `be5c763` (Fase 1), `8ecb669` (Fase 2) y
> `6d64fec` (Fase 3) en la rama `yc-roadmap-enhancement`. La guia de la Fase 4 es
> [`como-agregar-una-categoria.md`](./como-agregar-una-categoria.md).

## Contexto

El proyecto define la lista de categorias de noticias (`economia`, `politica`, `deportes`,
`tecnologia`, `entretenimiento`, `policiales`, `general`) en **seis lugares distintos** que no
estan sincronizados entre si. Esto ya produjo un bug concreto: `policiales` puede desaparecer de
la clasificacion automatica cuando el archivo de reglas no carga, y no tiene pestana en la pagina
de noticias aunque si existan articulos guardados con esa categoria.

Este documento no reemplaza [`docs/mejora-categorizacion/plan-categorizacion.md`](../mejora-categorizacion/plan-categorizacion.md),
que ataca la **precision** del clasificador (por que una nota se etiqueta mal). Este documento
ataca un problema distinto: la **lista de categorias validas** esta duplicada y desalineada, y no
hay un proceso claro para agregar una categoria nueva sin romper algo en el camino.

## Inventario: donde vive la lista de categorias hoy

| # | Ubicacion | Que define | Valores actuales |
|---|---|---|---|
| 1 | [`src/db/repository.py:54`](../../src/db/repository.py) `DEFAULT_CATEGORIES` | slug -> nombre visible; siembra la tabla `news_categories`; alimenta `/api/preferences/options` | economia, politica, deportes, tecnologia, entretenimiento, policiales, **general** (7) |
| 2 | [`src/config/settings.py:83`](../../src/config/settings.py) `default_categories` (env `DEFAULT_CATEGORIES`) | que categorias colecta y resume el pipeline principal (`src/main.py:187,532`) | economia, politica, deportes, tecnologia, entretenimiento, policiales (6, **sin general**) |
| 3 | `.env` (valor real en uso) | override de (2) para el entorno actual | economia, politica, deportes, tecnologia, entretenimiento, **general**, policiales (7, orden distinto) |
| 4 | `.env.local.example`, `.env.prod.example`, `docker-compose.yml:75` | valor por defecto sugerido para nuevos entornos | economia, politica, deportes, tecnologia, entretenimiento, policiales (6, **sin general**) |
| 5 | [`config/classification.yaml`](../../config/classification.yaml) `categories:` | reglas de clasificacion por categoria (pesos, keywords) | economia, politica, deportes, tecnologia, entretenimiento, policiales (6; `general` es el fallback implicito cuando nada califica) |
| 6 | [`src/processors/classifier.py:27`](../../src/processors/classifier.py) `FALLBACK_CATEGORIES` (solo si el YAML de (5) falla al cargar) | mismo rol que (5) pero hardcodeado como red de seguridad | economia, politica, deportes, tecnologia, entretenimiento (5, **sin policiales**) |
| 7 | [`frontend/src/pages/NewsPage.tsx:23`](../../frontend/src/pages/NewsPage.tsx) `categoryTabs` | pestanas de la pagina "Noticias" | general (= sin filtro), economia, politica, deportes, tecnologia, entretenimiento (6, **sin policiales**) |

La pagina de suscripcion (`SubscribePage.tsx`) es la unica pantalla que ya hace lo correcto: no
hardcodea nada, pide la lista a `/api/preferences/options`, que a su vez sale de (1).

## Los tres problemas concretos

### 1. El bug de "policiales" (el que reportaste)

`NewsClassifier.FALLBACK_CATEGORIES` (fila 6) es la lista que se usa **solo cuando
`config/classification.yaml` no se puede leer** (archivo movido, YAML invalido, permisos, etc. —
ver `_load_config` en `classifier.py`). Esa lista tiene 5 categorias, sin `policiales`. En ese
modo de fallback, `self.valid_categories` tampoco incluye `policiales`, asi que ninguna nota puede
clasificarse como tal: cae en `general` o se descarta segun el flujo. Mientras el YAML cargue bien
(caso normal hoy), esto es invisible — por eso es un bug latente, no uno que se vea todo el
tiempo, y por eso costo identificarlo.

### 2. "general" significa dos cosas distintas

- En el clasificador y la base de datos, `general` es una **categoria real**: el cajon donde cae
  una noticia que no encajo en ninguna categoria especifica (ejemplo real visto en el preview:
  notas sobre nevadas o sobre TikTok que no son ni politica ni deportes).
- En `NewsPage.tsx`, la pestana **"general" no filtra por esa categoria**: es la pestana "todas",
  sin parametro `category` en la URL. Un usuario que hace clic ahi ve TODO, no solo las notas
  clasificadas como `general`.

Mismo nombre, dos significados. Esto confunde tanto al usuario (¿por que "general" trae de todo?)
como a quien mantiene el codigo (¿el env var `DEFAULT_CATEGORIES` deberia o no incluir `general`?
Hoy la respuesta cambia segun el archivo que mires).

### 3. Agregar una categoria nueva hoy requiere tocar 7 lugares a mano

Si maniana quieres agregar `salud` como categoria, hay que recordar editar: el diccionario en
Python, el `.env` de cada entorno (dev, local, prod), el `docker-compose.yml`, las reglas en
`classification.yaml`, el fallback hardcodeado del clasificador, y el array hardcodeado del
frontend. Olvidar uno no rompe nada de forma ruidosa — simplemente la categoria queda "a medias"
en algun lugar, como paso con `policiales`. Es exactamente el riesgo que mencionaste.

## Fuente de verdad recomendada

`DEFAULT_CATEGORIES` en `src/db/repository.py` ya es, en la practica, la lista mas completa y la
unica que ya alimenta un endpoint publico (`/api/preferences/options`). Se recomienda declararla
formalmente como **la unica fuente de verdad para "que categorias existen"**, y que todo lo demas
la lea o haga fallback a ella — nunca al reves.

Separar dos preguntas que hoy estan mezcladas:

- **"Que categorias existen"** -> `DEFAULT_CATEGORIES` (fuente unica).
- **"Como se clasifica una nota en una de esas categorias"** -> `config/classification.yaml`
  (reglas, pesos, keywords). Este archivo puede seguir cambiando con frecuencia sin tocar la lista
  de categorias.

```
DEFAULT_CATEGORIES (src/db/repository.py)
        |
        +--> news_categories (tabla, sembrada al iniciar)
        |
        +--> /api/preferences/options  --> SubscribePage.tsx (ya OK)
        |                              --> NewsPage.tsx (a corregir: hoy hardcodeado)
        |
        +--> settings.categories_list (a corregir: hoy vive independiente en .env)
        |
        +--> NewsClassifier.valid_categories (a corregir: fallback sin policiales)
```

## Plan de implementacion (por fases, de menor a mayor riesgo)

### Fase 1 — Arreglar el bug urgente + validacion de consistencia (bajo riesgo)

- Agregar `policiales` a `FALLBACK_CATEGORIES` en `classifier.py`. Cambio aislado y sin efectos
  secundarios: solo cambia que pasa en el caso raro de que el YAML no cargue.
- Agregar una validacion al arrancar el backend que compare `DEFAULT_CATEGORIES`
  (`repository.py`) contra las categorias de `config/classification.yaml`, y **solo registre un
  warning en el log** (via `loguru`, mismo patron que ya usa el proyecto para "DB no disponible")
  si una categoria esta en un lado y no en el otro — sin bloquear el arranque ni fallar el
  proceso. El objetivo es que el desajuste sea visible en los logs (y detectable por Sentry, que
  ya esta conectado) en vez de silencioso como paso con `policiales`, sin arriesgar que un typo en
  el YAML tumbe todo el backend en produccion.

### Fase 2 — Unificar el env var con la fuente de verdad (riesgo bajo-medio)

- Cambiar `settings.py` para que, si `DEFAULT_CATEGORIES` no esta seteado en el entorno, el
  default sea generado desde `DEFAULT_CATEGORIES` de `repository.py` en vez de un string
  hardcodeado aparte (evita que las dos listas puedan volver a desincronizarse).
- Igualar `.env`, `.env.example`, `.env.local.example`, `.env.prod.example` y
  `docker-compose.yml` al mismo valor y orden.
- Nota: esto **si cambia comportamiento real** — `settings.categories_list` controla que
  categorias colecta y resume `src/main.py` en cada corrida. Ver riesgos abajo.

### Fase 3 — Frontend: pestanas dinamicas + solo mostrar categorias con noticias

- `NewsPage.tsx` deja de hardcodear `categoryTabs` y pide la lista a
  `/api/preferences/options`, igual que ya hace `SubscribePage.tsx`. Esto resuelve el problema de
  fondo de raiz: agregar una categoria nueva en el backend hace que aparezca sola en el frontend,
  sin tocar el componente.
- Para "que solo se muestren las categorias que tienen noticias" (lo que pediste), se necesita un
  endpoint nuevo y liviano — hoy no existe forma de saber cuantas notas hay por categoria sin
  pedir cada categoria por separado. Propuesta: `GET /api/news/category-counts?date=YYYY-MM-DD&view=resumenes|recolectadas`,
  que devuelve `[{slug, label, count}]` con un `GROUP BY category_id` sobre la tabla que
  corresponda (`news_summaries` o `news_articles`) filtrado a esa fecha. `NewsPage.tsx` oculta las
  pestanas con `count === 0` y muestra siempre "Todas" (la pestana sin filtro, renombrada para no
  llamarse "general" y dejar de chocar con la categoria real).
- Renombrar la pestana "todas noticias" en la UI (hoy dice "general") a un label que no colisione
  con la categoria `general` real, por ejemplo "Todas".

### Fase 4 — Documentar el proceso de agregar una categoria nueva

Una vez completadas las fases 1-3, agregar una categoria nueva debería reducirse a dos ediciones
de archivo y un reinicio. Ese procedimiento se documenta como una guia aparte, pensada para
seguirse paso a paso sin tener que leer este plan completo:
[`docs/mejorar-comportamiento-categorias/como-agregar-una-categoria.md`](./como-agregar-una-categoria.md).

Se agrega tambien un comentario corto arriba de `DEFAULT_CATEGORIES`, apuntando a esa guia, para
que quien la edite en el futuro sepa que hay un segundo paso pendiente sin tener que buscarlo.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Cambiar `settings.categories_list` afecta que categorias colecta/resume `src/main.py` en produccion — un error aqui puede dejar de generar briefs para una categoria real. | Alto (afecta el pipeline que corre en cron/produccion) | Hacer el cambio de Fase 2 en un entorno de staging/local primero; verificar con una corrida manual (`trigger/summary`) que las 7 categorias aparecen en el resultado antes de tocar produccion. |
| El endpoint nuevo de conteos (Fase 3) puede ser lento si no hay indice por `category_id` + fecha. | Medio (latencia en la pagina de noticias) | Revisar que `news_summaries`/`news_articles` ya tengan indice compuesto por fecha+categoria antes de habilitarlo (probable que ya exista por `summary_date` indexado); si no, agregar migracion de indice. |
| Renombrar la pestana "general" a "Todas" es un cambio de UI visible; usuarios que compartieron un link con `?category=` sin valor no se ven afectados, pero el texto cambia. | Bajo | Es solo texto, no cambia la URL ni el comportamiento — no requiere migracion de datos ni redirects. |
| Unificar los `.env*` puede pisar un valor que algun entorno real (staging/prod) tenga customizado a proposito. | Medio | Antes de sobreescribir, revisar si el `.env` de produccion real (fuera del repo, en el servidor) tiene un valor distinto y por que; si es intencional, documentarlo en vez de forzar la unificacion. |
| Categorias historicas: si en el futuro se **elimina** una categoria de `DEFAULT_CATEGORIES` en vez de agregarla, las notas ya guardadas con esa categoria quedan huerfanas (FK a una fila que ya no se resiembra activamente, aunque no se borra). | Bajo (no rompe nada hoy, pero puede sorprender) | Documentar que quitar una categoria requiere decidir que pasa con las notas existentes (reclasificar, archivar, o dejarlas con su categoria historica) — no esta en alcance de este plan, solo se deja anotado. |

## Fuera de alcance

- Mejorar la precision del clasificador (falsos positivos de keywords) — eso ya esta cubierto por
  `docs/mejora-categorizacion/`.
- Migrar a una taxonomia externa tipo IPTC — mencionado como idea futura en el otro documento, no
  es necesario para resolver la desalineacion actual.
