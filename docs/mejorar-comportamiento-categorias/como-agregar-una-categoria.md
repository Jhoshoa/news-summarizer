# Como agregar una categoria nueva

Guia paso a paso para agregar una categoria de noticias al sistema (por ejemplo `salud`). Asume
que ya se aplico el plan en [`plan-categorias.md`](./plan-categorias.md) (Fases 1-3): una sola
fuente de verdad y todo lo demas leyendo de ahi. Si tu version del proyecto todavia no tiene esas
fases aplicadas, revisa primero ese documento — los pasos de abajo suponen que ya no hay listas
duplicadas por sincronizar a mano.

## Antes de empezar

Define, en una frase, que noticias deberian caer en esta categoria y cuales NO. Ejemplo para
`salud`: "noticias sobre hospitales, enfermedades, vacunacion y sistema de salud publico o
privado — no incluye deportes de alto rendimiento ni politicas economicas del sector salud, eso
sigue siendo `politica` o `deportes` segun el enfoque de la nota." Esta frase es la que vas a
convertir en las palabras clave del paso 2.

## Pasos

### 1. Agregar la categoria a la fuente de verdad

Editar `DEFAULT_CATEGORIES` en [`src/db/repository.py`](../../src/db/repository.py):

```python
DEFAULT_CATEGORIES = {
    "economia": "Economia",
    "politica": "Politica",
    "deportes": "Deportes",
    "tecnologia": "Tecnologia",
    "entretenimiento": "Entretenimiento",
    "policiales": "Policiales",
    "salud": "Salud",       # <- nueva
    "general": "General",
}
```

- La clave (`salud`) es el slug: minusculas, sin espacios ni acentos, se usa en URLs y en la base
  de datos. No lo cambies despues de tenerlo en produccion — cambiar un slug existente rompe
  enlaces y filtros ya guardados.
- El valor (`Salud`) es el nombre que ve el usuario. Este si se puede ajustar despues sin romper
  nada, es solo texto.

### 2. Agregar las reglas de clasificacion

Editar [`config/classification.yaml`](../../config/classification.yaml) y agregar un bloque nuevo
bajo `categories:`, con el mismo formato que las categorias existentes:

```yaml
categories:
  salud:
    description: "Salud, hospitales, enfermedades y sistema sanitario."
    positive:
      - { term: "hospital", weight: 3 }
      - { term: "vacuna", weight: 3 }
      - { term: "\\bsalud\\b", weight: 2, regex: true }
    negative:
      - { term: "salud economica", weight: 4 }   # evita falsos positivos con economia
```

Consejos (ver tambien `docs/mejora-categorizacion/plan-categorizacion.md` para el detalle de como
funciona el scoring):

- Usa `regex: true` con fronteras de palabra (`\b`) para palabras cortas o ambiguas, para no
  matchear substrings dentro de otras palabras.
- Agrega `negative` para los casos donde tu categoria se confunde con otra existente (como el
  ejemplo de "salud economica" arriba, para no robarle notas a `economia`).
- Si algun sitio scrapeado ya tiene su propia etiqueta para esto (por ejemplo la fuente lo llama
  `sanidad` o `medicina`), agregalo tambien a `source_category_mappings` mas abajo en el mismo
  archivo, igual que existe hoy para `policiales` (`seguridad`, `policial`, `crimen`, etc.).

**Este paso no es opcional.** Si el paso 1 se hace sin el paso 2, la categoria queda "registrada"
pero el clasificador nunca le va a asignar ninguna nota — todo seguira cayendo en `general`. El
backend te va a avisar de este desajuste con un warning en los logs al arrancar (ver
"Como saber si algo quedo a medias" abajo), pero no va a bloquear el arranque.

### 3. Reiniciar el backend

- La tabla `news_categories` se siembra automaticamente al iniciar (`_seed_categories` en
  `repository.py`), asi que no hace falta ninguna migracion SQL manual para que la categoria nueva
  exista en la base de datos.
- `config/classification.yaml` se recarga cuando el proceso arranca. Si estas corriendo con
  Docker: `docker compose build backend && docker compose up -d backend` (o el equivalente en tu
  `docker-compose.local.yml`).

### 4. Verificar

- `GET /api/preferences/options` debe incluir `salud` en `categories`.
- La pagina de suscripcion (`/suscribirse`) debe mostrar el checkbox de "Salud" sin tocar codigo
  de frontend.
- La pagina de noticias (`/news`) debe mostrar la pestana "Salud" una vez que haya al menos una
  nota clasificada asi (las pestanas sin noticias no se muestran, ver Fase 3 del plan).
- Correr una coleccion manual (`POST /trigger/summary` o el boton de refrescar) y revisar en los
  logs que aparezcan notas clasificadas como `salud`. Si no aparece ninguna, probablemente las
  keywords del paso 2 son muy especificas o no coinciden con el texto real de las fuentes — ajusta
  y vuelve a probar, no es un error de configuracion sino de afinar las reglas.

### Como saber si algo quedo a medias

Al arrancar, el backend compara `DEFAULT_CATEGORIES` contra las categorias definidas en
`classification.yaml` y registra un warning (visible en logs y en Sentry) si encuentra una
categoria en un lado que no esta en el otro. Si ves ese warning despues de agregar una categoria,
revisa que hiciste los pasos 1 y 2 — no falla el arranque, pero es la senal de que algo quedo
desalineado.

## Que NO hace falta tocar

Si las Fases 1-3 del plan ya estan aplicadas, estos archivos **ya no requieren edicion manual**
al agregar una categoria (antes si, y era la causa de que `policiales` quedara incompleto en
varios lugares):

- `.env`, `.env.example`, `.env.local.example`, `.env.prod.example`, `docker-compose.yml`
- `src/config/settings.py`
- `src/processors/classifier.py` (`FALLBACK_CATEGORIES`)
- `frontend/src/pages/NewsPage.tsx`

Si notas que alguno de estos archivos todavia tiene una lista de categorias hardcodeada, es senal
de que las Fases 1-3 no se completaron del todo — revisa `plan-categorias.md`.

## Quitar una categoria

Este documento cubre solo agregar. Quitar una categoria existente es una operacion distinta y mas
delicada (que pasa con las notas ya guardadas con esa categoria) — no esta cubierta aca, ver la
seccion de riesgos en `plan-categorias.md`.
