# Capítulo 6 — Alineación con Green Tech

EcoBrief Bolivia encaja en Green Tech porque promueve un uso más eficiente y responsable de software, datos e inteligencia artificial. Los principios se mantienen respecto a la versión anterior; lo que cambió es la evidencia concreta que los respalda.

## 6.1 Reducción de navegación innecesaria

El usuario no necesita abrir múltiples páginas para entender los hechos principales. El sistema entrega una síntesis priorizada que reemplaza la navegación dispersa. Ahora, además, cuando varias fuentes cubren la misma historia, el usuario recibe **un solo resumen agrupado** en vez de una versión por medio.

## 6.2 Reducción de duplicación informativa

La deduplicación evita que la misma historia sea procesada y mostrada varias veces. Esto ya no depende de un único criterio: opera en cuatro capas (lote, huella histórica, agrupación por historia y verificación semántica con IA), reduciendo el almacenamiento, el ancho de banda y las llamadas a la IA para contenido redundante de forma más robusta que en la versión anterior.

## 6.3 Reducción de llamadas IA redundantes

La IA se usa después de limpiar, filtrar, deduplicar, agrupar por historia y rankear. La agrupación de historias en particular evita invocar al modelo una vez por cada fuente que cubre el mismo hecho — una reducción de llamadas que no existía en la versión 1. A esto se suma que, ante la falla de un proveedor, el sistema conmuta automáticamente a otro en vez de reintentar indefinidamente contra el mismo, evitando cómputo desperdiciado en reintentos fallidos.

## 6.4 Reducción de consumo de datos

El usuario puede leer resúmenes compactos en lugar de cargar páginas completas con imágenes, publicidad, *trackers* y scripts. La estimación de ahorro por página evitada se mantiene sin cambios respecto a la versión anterior.

## 6.5 Promoción del consumo digital responsable

Las preferencias por categoría, canal y **hora de entrega** reducen la información no solicitada y evitan el *spam* informativo. El usuario elige qué recibir, por qué canal y en qué momento del día.

## 6.6 Reducción de dependencia del scroll social

EcoBrief ofrece una alternativa al consumo informativo en redes sociales. El usuario recibe resúmenes compactos, priorizados y enlazados a fuentes identificadas, ahora con el nivel de confianza de cada afirmación explícito (confirmada por múltiples fuentes, basada en declaración oficial, o de una sola fuente).

## 6.7 Trazabilidad y confianza informativa

Este es el punto donde más avanzó el sistema desde la versión anterior. Ya no basta con conservar el enlace a la fuente original: cada afirmación de un resumen debe respaldarse en un artículo real, con un fragmento de evidencia verificable. El sistema descarta explícitamente cualquier afirmación cuya evidencia no pueda validarse contra un artículo existente, en vez de confiar en lo que el modelo de lenguaje "recuerda" o infiere. Esto no reemplaza el *fact-checking* periodístico, pero reduce activamente la dependencia de afirmaciones sin fuente verificable — el mismo estándar de trazabilidad se aplicó, en esta misma semana de trabajo, a los propios datos del sistema: dos errores de scraping de indicadores económicos se detectaron comparando el dato mostrado contra la fuente original y se corrigieron con pruebas de regresión antes de desplegar.
