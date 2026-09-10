# Capítulo 5 — Costos y Sostenibilidad Económica

EcoBrief sigue diseñado para operar con bajo costo: los cuatro servicios (base de datos, backend, frontend y cron-job) corren como contenedores Docker Compose sobre un mismo VPS, sin necesidad de infraestructura adicional por haber separado el cron-job del backend.

> **Nota de alcance:** esta revisión se enfocó en el código y la arquitectura, no en verificar facturas o contratos vigentes de hosting. Los montos de infraestructura de esta sección se mantienen de la versión anterior como referencia y **no fueron reverificados** en esta actualización; sí se confirmaron en el código los cambios que afectan directamente el perfil de costo (proveedores de IA y canal de WhatsApp).

## 5.1 Infraestructura (referencial, sin reverificar en esta revisión)

| Componente | Proveedor | Costo referencial |
|---|---|---:|
| Servidor VPS | Hostinger KVM 2 | USD 107.88/año |
| Dominio | NIC Bolivia | 55 Bs/año |
| Base de datos, backend, frontend, cron-job | Contenedores en el mismo VPS | Incluido |
| Email | Gmail SMTP + App Password | Gratuito* |
| Telegram | Bot API | Gratuito |
| IA | Groq / Gemini / GitHub Models *free tier* | Gratuito / variable |

*Dentro de los límites de envío de Google; migrable a un proveedor SMTP dedicado si se supera el límite.

## 5.2 Cambio relevante: salida de Twilio

La versión anterior consideraba WhatsApp vía Twilio como canal opcional, con un costo variable desde USD 0.0116/minuto saliente. Esa dependencia **ya no existe**: el sistema migró a la API oficial de Meta (WhatsApp Cloud API) de forma directa, sin intermediario. Esto elimina tanto el margen que Twilio cobraba sobre la tarifa base de Meta como la exigencia de recarga automática obligatoria que motivó el cambio. El costo de mensajería de WhatsApp pasa a depender directamente de la tarifa pública de Meta, sin capa adicional.

## 5.3 Ampliación de proveedores de IA

La versión anterior consideraba 3 proveedores (Groq, OpenAI, GitHub Models). Hoy el enrutador soporta 5, incluyendo **Gemini** y **NVIDIA**, ambos con niveles gratuitos utilizables en las tareas de clasificación y revisión de ambigüedad. Esto no solo agrega resiliencia (Capítulo 3.5.1): también amplía el margen antes de tener que recurrir a un proveedor de pago como OpenAI, cuyo costo por token de salida es sensiblemente mayor al de Groq o DeepSeek.

| Proveedor | Modelo de referencia | Input / 1M tok. | Output / 1M tok. |
|---|---|---:|---:|
| Groq | Llama 3.3 70B Versatile | USD 0.59 | USD 0.79 |
| OpenAI | GPT-4.1 mini | USD 0.75 | USD 4.50 |
| DeepSeek | V4 Flash | USD 0.14 | USD 0.28 |
| Anthropic | Claude Haiku 4.5 | USD 1.00 | USD 5.00 |

*(Tabla de precios de referencia sin reverificar en esta revisión; los modelos realmente activos en el enrutador se listan en el Capítulo 3.5.1.)*

## 5.4 Control de costos

El sistema reduce costos operativos mediante las mismas estrategias de la versión anterior, ahora reforzadas:

- No resume todo lo recolectado: filtra, deduplica, agrupa por historia y rankea primero.
- La agrupación de historias evita generar un resumen distinto por cada fuente que cubre el mismo hecho — una reducción de llamadas IA que no existía en la v1.
- Cachea resultados y limita candidatos por categoría.
- Usa modelos pequeños y gratuitos para tareas simples (clasificación, revisión de ambigüedad), reservando modelos de mayor capacidad para la síntesis final.
- *Timeouts* agresivos (45 s) y un solo reintento por proveedor evitan que una llamada colgada consuma cómputo o tiempo de espera innecesario.
- Telegram y (ahora) WhatsApp directo con Meta como canales sin intermediario de costo variable.

## 5.5 Escenario operativo actual

El sistema ya opera con este enfoque, no como recomendación a futuro:

1. Los 4 servicios corren en un mismo VPS vía Docker Compose.
2. El enrutador LLM prioriza proveedores gratuitos (Groq, Gemini) antes de recurrir a OpenAI.
3. Telegram y WhatsApp (Meta) operan sin costo de intermediario por mensaje.
4. El refresco de indicadores económicos y la generación de resúmenes corren en cadencias moderadas (10–30 min y horas fijas respectivamente) para no generar tráfico ni cómputo innecesario.

Queda pendiente, para una futura revisión de este capítulo, verificar directamente con el equipo el gasto real acumulado de los últimos meses frente a estas estimaciones.
