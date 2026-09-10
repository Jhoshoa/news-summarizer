# Capítulo 2 — Marco Conceptual

## 2.1 Desperdicio digital informativo

El concepto de desperdicio digital se refiere al consumo innecesario de recursos tecnológicos —datos, energía, tiempo de procesamiento y atención humana— que no agregan valor al usuario final. En el contexto informativo, el desperdicio ocurre cuando:

- Un usuario carga múltiples páginas web para obtener información que podría presentarse en un solo formato compacto.
- El mismo contenido es procesado y almacenado varias veces por sistemas automatizados, incluso cuando proviene de fuentes distintas pero cubre el mismo hecho.
- Los modelos de IA reciben y procesan contenido redundante o de baja calidad, o repiten una llamada porque el proveedor elegido falló sin un mecanismo de recuperación.
- Las redes sociales exponen a los usuarios a información fragmentada, repetida o sin contexto, incentivando el *scroll* continuo.

Este desperdicio tiene un costo real: consumo energético en servidores y dispositivos, emisiones de carbono asociadas a la transmisión y procesamiento de datos, y agotamiento de la capacidad de atención de las personas.

## 2.2 Green Tech y sostenibilidad digital

**Green Tech** (Tecnología Verde) es un enfoque que busca diseñar, desarrollar y utilizar tecnología minimizando su impacto ambiental y promoviendo la sostenibilidad. En el ámbito del software y los datos, esto implica:

- Eficiencia en el uso de recursos computacionales.
- Reducción de datos innecesarios almacenados y transmitidos.
- Optimización de consultas a modelos de IA, incluyendo el uso deliberado de modelos pequeños para tareas simples y modelos de mayor capacidad solo cuando la tarea lo justifica.
- Diseño de sistemas que promuevan hábitos de consumo digital responsable.

EcoBrief Bolivia se enmarca en esta corriente al atacar directamente el desperdicio informativo: reduce la cantidad de páginas que un usuario necesita cargar, elimina la redundancia en el procesamiento de contenido —incluso entre fuentes distintas que cubren la misma historia— y optimiza el uso de modelos de lenguaje.

## 2.3 Inteligencia artificial responsable

La IA responsable busca que los sistemas de inteligencia artificial sean éticos, transparentes, eficientes, sostenibles y **resilientes**. En EcoBrief, la IA se utiliza solo después de que el contenido ha sido filtrado, deduplicado, agrupado por historia y priorizado. Esto significa que:

- No se envía contenido irrelevante o repetido al modelo.
- Se utilizan modelos pequeños y rápidos para tareas simples (clasificación, revisión de ambigüedad) y modelos más capaces para la síntesis final.
- Los resultados se cachean para evitar reprocesamiento.
- Se limita el número de candidatos por categoría.
- Ningún proveedor de IA es un punto único de falla: si uno falla o se degrada, el sistema conmuta automáticamente a otro sin detener la corrida.
- Cada afirmación generada por el modelo debe respaldarse en un artículo real existente en la base de datos — el sistema descarta explícitamente cualquier afirmación cuya evidencia no pueda verificarse, en vez de confiar ciegamente en lo que el modelo "recuerda" o infiere.

De esta forma, la IA se convierte en una herramienta de reducción y verificación, no de multiplicación de contenido ni de afirmaciones sin respaldo.
