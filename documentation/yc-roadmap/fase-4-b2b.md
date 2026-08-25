# Fase 4 — EcoBrief Intelligence (B2B)

**Aquí empieza el negocio defendible y el que se puede mostrar a YC con MRR real.**

**Estado actual:** no existe nada de esto en el repo. Cero multi-tenant, cero
facturación, cero alertas a nivel de organización.

**Tiempo estimado:** ~5 semanas de construcción (workspaces + monitores 2 sem,
informes 1 sem), pero **las entrevistas y primeros pilotos deben arrancar en paralelo
desde la semana 1**, no esperar a tener el producto B2B terminado.

## 4.1 Espacios de trabajo (workspaces)

```sql
CREATE TABLE organizations (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  plan VARCHAR(30) NOT NULL DEFAULT 'trial',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE workspace_members (
  organization_id BIGINT NOT NULL REFERENCES organizations(id),
  subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
  role VARCHAR(20) NOT NULL DEFAULT 'reader',  -- owner, admin, analyst, reader
  PRIMARY KEY (organization_id, subscriber_id)
);
```

No se necesita RBAC complejo al inicio — 4 roles fijos alcanzan.

## 4.2 Monitores

Ejemplo: "Noticias sobre minería, litio, regulación ambiental y bloqueos en Bolivia."

```sql
CREATE TABLE monitors (
  id BIGSERIAL PRIMARY KEY,
  organization_id BIGINT NOT NULL REFERENCES organizations(id),
  name VARCHAR(200) NOT NULL,
  keywords TEXT[] NULL,
  entity_ids BIGINT[] NULL,        -- referencia a entities (Fase 3.2)
  categories TEXT[] NULL,
  regions TEXT[] NULL,
  included_sources TEXT[] NULL,
  excluded_sources TEXT[] NULL,
  importance_threshold VARCHAR(20) NULL,
  frequency VARCHAR(20) NOT NULL DEFAULT 'daily',
  recipients TEXT[] NULL
);
```

Depende de Fase 3.2 (entidades) y Fase 1 (historias) para tener algo que monitorear
que no sea solo un artículo suelto.

## 4.3 Alertas inteligentes

Tipos: nueva historia importante, cambio relevante en una historia, nueva mención de
empresa, publicación de normativa, aumento inusual de cobertura, contradicción entre
fuentes, riesgo reputacional, nueva fuente oficial.

**Regla clave: la unidad de alerta es la historia o el cambio, nunca el artículo
individual** — esto evita el error común de saturar al cliente pagado con ruido.
Depende directamente del modelo de actualizaciones incrementales de Fase 1.4.

## 4.4 Informes automáticos

Formatos: brief diario, resumen semanal, informe por industria, seguimiento de crisis,
evolución de una historia, resumen ejecutivo. Salida inicial: Email + PDF + CSV +
enlace privado. API/webhook después, no ahora.

## 4.5 Búsqueda avanzada

Filtros: fecha, país, departamento, ciudad, categoría, entidad, fuente, estado de
historia, confianza, cantidad de cobertura, tipo de evento. Es una capa de consulta
sobre las tablas ya definidas en Fases 1–3; no requiere infraestructura nueva
(Postgres con índices adecuados alcanza a esta escala).

## 4.6 Exportación

Inicial: PDF ejecutivo, CSV de historias, enlace compartible. Después: API, webhooks,
Slack/Teams/correo.

## 4.7 Facturación

Planes: Personal gratuito, Personal Pro, Intelligence.

**No dediques semanas a construir facturación antes de tener clientes.** Cobra
manualmente a los primeros (transferencia, Stripe payment link, o similar) y otorga
acceso desde el panel admin (Fase 5) marcando el `plan` de la organización a mano.
Automatizar facturación es una tarea de fase posterior, después de validar precio y
disposición a pagar.

## Criterio de salida

Entre 5 y 10 organizaciones usando informes reales. Idealmente al menos 3 pagando.
