# Distribución - Plan de Implementación

**Última actualización:** 2026-07-15
**Objetivo:** Establecer canales de distribución funcionales y gratuitos para MVP

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Comparativa de Proveedores SMTP Gratuitos](#2-comparativa-de-proveedores-smtp-gratuitos)
3. [Recomendación: Brevo (Sendinblue)](#3-recomendación-brevo)
4. [Configuración de Telegram Bot](#4-configuración-de-telegram-bot)
5. [Ajustes Necesarios en la Aplicación](#5-ajustes-necesarios-en-la-aplicación)
6. [Estrategia de Pruebas](#6-estrategia-de-pruebas)
7. [Análisis de Riesgos y Mitigación](#7-análisis-de-riesgos-y-mitigación)
8. [Checklist de Implementación](#8-checklist-de-implementación)
9. [Referencias](#9-referencias)
10. [Decisiones Pendientes](#10-decisiones-pendientes)

---

## 1. Resumen Ejecutivo

### Canales de Distribución (Priorizados)

| Canal | Costo | Estado | Prioridad |
|-------|-------|--------|-----------|
| **Telegram Bot** | $0 (gratis) | Implementado, no testeado | **P1** |
| **Email SMTP** | $0 (free tier) | Funciona local, falla en deploy | **P1** |
| **WhatsApp (Twilio)** | $1/mes + $0.01/msg | Implementado | P3 (post-MVP) |

### Meta

- **Corto plazo (1 semana):** Telegram + Email funcionando en producción
- **Mediano plazo (1 mes):** 10+ suscriptores activos
- **Largo plazo (3 meses):** WhatsApp con Twilio para tier premium

---

## 2. Comparativa de Proveedores SMTP Gratuitos

### Requisitos para EcoBrief

- **Volumen:** 50-200 emails/día (1500-6000/mes)
- **Tipo:** Transaccional (briefs de noticias)
- **Costo:** $0 (free tier forever)
- **API:** SMTP + API (ideal)
- **Dominio:** Soporte para dominio propio

### Tabla Comparativa

| Proveedor | Free Tier | Diario | API | Dominio Propio | Limitaciones | Recomendado |
|-----------|-----------|--------|-----|----------------|--------------|-------------|
| **Brevo** | 9,000/mes | 300/día | ✅ | ✅ | Marca de agua en free tier | ⭐ SÍ |
| **Mailtrap** | 1,000/mes | 200/día | ✅ | ✅ | 1 dominio en free | Sí |
| **SendGrid** | 100/día | 100 | ✅ | ✅ | 100/día = 3000/mes | Sí |
| **Mailgun** | 5,000/mes | 300/día | ✅ | ✅ | Requiere tarjeta | No |
| **Elastic Email** | 3,000/mes | 100/día | ✅ | ✅ | 100/día | Sí |
| **Maileroo** | 3,000/mes | - | ✅ | ✅ | - | Sí |
| **Amazon SES** | 62,000/mes (EC2) | - | ✅ | ✅ | Complejo setup | No |
| **Gmail App Password** | 500/día | 500 | SMTP | ❌ | No profesional, rate limits | No |

### Detalle por Proveedor

#### Brevo (Ex-Sendinblue) — ⭐ RECOMENDADO

```
Free Tier: 9,000 emails/mes (300/día)
SMTP: smtp-relay.brevo.com:587
API: REST + SMTP
Dominio: Propio (con verificación DNS)
```

**Ventajas:**
- 9,000 emails/mes gratis = cubre 150+ suscriptores con briefs diarios
- API robusta con webhooks para bounce/complaint
- Dashboard de analytics incluido
- Soporte SPF/DKIM/DMARC
- Sin marca de agua en remitente (puedes usar tu dominio)

**Desventajas:**
- Free tier incluye marca de agua en pie de email (removible con dominio propio)
- Requiere verificación de dominio (15 min)

**Setup:**
1. Crear cuenta en https://www.brevo.com
2. Agregar dominio en Settings → Sending Domains
3. Configurar registros DNS (SPF, DKIM, DMARC)
4. Obtener credenciales SMTP
5. Actualizar `.env`:

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=tu@email.com
SMTP_PASSWORD=tu_api_key_aqui
SMTP_FROM_EMAIL=briefs@tudominio.com
SMTP_FROM_NAME=EcoBrief Bolivia
```

#### Mailtrap

```
Free Tier: 1,000 emails/mes (200/día)
SMTP: smtp.mailtrap.io:587
API: REST + SMTP
```

**Ventajas:**
- Dashboard de prueba incluido
- Sin límite de dominios (1 activo)
- Ideal para development/testing

**Desventajas:**
- 1,000/mes puede ser poco si creces rápido
- Logs retención limitada

#### SendGrid

```
Free Tier: 100 emails/día (~3,000/mes)
SMTP: smtp.sendgrid.net:587
API: REST + SMTP
```

**Ventajas:**
- Infraestructura robusta (Twilio)
- Templates dinámicos
- Analytics detallado

**Desventajas:**
- 100/día límite estricto
- Soporte limitado en free tier

---

## 3. Recomendación: Brevo

### Por qué Brevo sobre otras opciones

1. **Volumen:** 9,000/mes vs 3,000 de competidores
2. **Fiabilidad:** Enterprise-grade infrastructure
3. **Costo futuro:** $25/mes por 20,000 emails (escalar sin cambiar de proveedor)
4. **Comunidad:** Documentación en español, soporte activo
5. **Integración:** Webhooks para tracking de aperturas/clicks

### Cálculo de Capacidad

```
200 suscriptores × 1 brief/día = 200 emails/día
200 × 30 días = 6,000 emails/mes
Brevo free tier: 9,000/mes ✅ (con margen del 50%)
```

---

## 4. Configuración de Telegram Bot

### 4.1 Crear el Bot (10 min)

1. Abrir Telegram → buscar `@BotFather`
2. Enviar `/newbot`
3. Nombre: `EcoBrief Bolivia`
4. Username: `ecobrief_bo_bot` (debe terminar en `_bot`)
5. Copiar token: `123456:ABCdefGHIjklMNOpqrsTUVwxyz`

### 4.2 Variables de Entorno

```env
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://tudominio.com/telegram/webhook
```

### 4.3 Estrategia de Deployment

| Método | Cuándo usar | Pros | Contras |
|--------|-------------|------|---------|
| **Polling** | Desarrollo local | Simple, sin servidor público | No funciona en producción |
| **Webhook** | Producción | Eficiente, real-time | Requiere HTTPS público |

**Recomendación:**
- **Local:** Polling (ya funciona con `python-telegram-bot`)
- **Producción:** Webhook via FastAPI endpoint

### 4.4 Configuración Webhook en Producción

El webhook ya está parcialmente implementado en `src/main.py`. Necesita:

1. **Endpoint receptor** (ya existe: `/telegram/webhook`)
2. **Certificado SSL** (tu VPS ya debe tener)
3. **URL pública** (tu dominio con HTTPS)

**Verificar endpoint actual:**
```bash
curl https://tudominio.com/telegram/webhook
# Debería retornar 405 Method Not Allowed (espera POST)
```

**Registrar webhook con Telegram:**
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://tudominio.com/telegram/webhook" \
  -d "allowed_updates=[\"message\",\"callback_query\"]"
```

---

## 5. Ajustes Necesarios en la Aplicación

### 5.1 Email: Arreglar Deploy (CRÍTICO)

**Problema actual:** Email funciona local pero no en producción.

**Causa probable:** Variables de entorno no configuradas en hosting.

**Solución:**
1. Verificar variables en hosting dashboard
2. Logs: buscar `SMTP no configurado` o `Email handler inicializado sin SMTP`
3. Probar conexión SMTP manualmente:

```python
# Test script (ejecutar en el servidor)
import smtplib
with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=10) as smtp:
    smtp.starttls()
    smtp.login("tu@email", "tu_api_key")
    print("Conexión exitosa")
```

**Posibles fixes en código:**

En `src/distributors/email_handler.py`, agregar retry logic:

```python
import smtplib
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _send_sync(self, message: EmailMessage) -> None:
    # ... existing code
```

### 5.2 Telegram: Ajustes de Producción

**Cambios necesarios en `src/distributors/telegram_handler.py`:**

1. **Rate limiting:** Telegram limita a 30 msgs/segundo por bot
2. **Error handling:** Reintentar en errores de red
3. **Logging:** Loggear errores sin exponer tokens

### 5.3 Logging de Distribución

Agregar métricas de envío para debugging:

```python
# En _deliver_summaries, agregar:
logger.info(
    "delivery_complete",
    channel=channel,
    success=delivered,
    recipient_id=recipient_id[:8],  # Anonimizado
    timestamp=datetime.now().isoformat()
)
```

---

## 6. Estrategia de Pruebas

### 6.1 Pruebas de Email

#### Local (desarrollo)

```bash
# 1. Configurar variables en .env
SMTP_HOST=smtp.mailtrap.io  # Mailtrap para testing
SMTP_USERNAME=tu_user
SMTP_PASSWORD=tu_pass

# 2. Ejecutar test
python -c "
from src.distributors.email_handler import EmailHandler
from src.config.settings import Settings
import asyncio

settings = Settings()
handler = EmailHandler(settings=settings)
result = asyncio.run(handler.send_message(
    to_email='test@example.com',
    subject='Test EcoBrief',
    body='Este es un test'
))
print(f'Enviado: {result}')
"
```

#### Producción

```bash
# Usar Brevo sandbox primero
curl -X POST http://localhost:8000/api/test-email \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"email": "tu@gmail.com"}'
```

### 6.2 Pruebas de Telegram

#### Local (polling)

```bash
# 1. Configurar token en .env
TELEGRAM_BOT_TOKEN=123456:ABC...

# 2. Ejecutar bot
python -m src.main

# 3. En Telegram, buscar tu bot → enviar /start
```

#### Producción (webhook)

```bash
# 1. Verificar webhook activo
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# 2. Test manual de envío
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" \
  -d "text=Test EcoBrief"
```

### 6.3 Pruebas End-to-End

```bash
# 1. Crear suscriptor via API
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "telegram_id": "12345678",
    "categories": ["economia", "politica"]
  }'

# 2. Trigger delivery
curl -X POST http://localhost:8000/trigger/delivery \
  -H "Authorization: Bearer $API_KEY"

# 3. Verificar recepción
# - Email: revisar bandeja/spam
# - Telegram: debería llegar mensaje al bot
```

---

## 7. Análisis de Riesgos y Mitigación

### 7.1 Riesgos Críticos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Email llega a spam** | Alta | Alto | Configurar SPF/DKIM/DMARC; usar dominio propio; warmup de IP |
| **Telegram webhook falla** | Media | Alto | Monitoreo de health endpoint; alertas en error rate > 5% |
| **Rate limiting en Brevo** | Baja | Medio | Implementar cola de envío; monitorear uso diario |
| **Variables de entorno faltantes** | Alta | Crítico | Checklist de deploy; test de salud al startup |

### 7.2 Riesgos Operacionales

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Suscriptores no reciben emails** | Media | Alto | Verificación de email; double opt-in; monitoreo de bounces |
| **Costos inesperados de LLM** | Baja | Medio | Rate limiting por usuario; cache de summaries |
| **Spam reports** | Media | Alto | Fácil baja; límite de 1 email/día; contenido relevante |
| **Token de Telegram comprometido** | Baja | Crítico | Rotación periódica; nunca en logs; variables de entorno |

### 7.3 Estrategias de Mitigación

#### Prevención de Spam (Email)

```
1. SPF Record: v=spf1 include:sendgrid.net ~all
2. DKIM: Configurar en DNS (proporcionado por Brevo)
3. DMARC: v=DMARC1; p=quarantine; rua=mailto:admin@tudominio.com
4. Warmup: Enviar 50 emails/día la primera semana, incrementar gradualmente
5. Contenido: Incluir enlace de baja; no usar palabras de spam
```

#### Rate Limiting (Telegram)

```python
# En telegram_handler.py, agregar:
from asyncio import Semaphore

_semaphore = Semaphore(30)  # Max 30 msgs/segundo

async def send_message(self, chat_id: str, message: str) -> bool:
    async with _semaphore:
        # ... existing code
```

#### Monitoreo de Salud

```python
# Health endpoint (agregar en main.py)
@app.get("/health/distribution")
async def distribution_health():
    return {
        "email_configured": self.email.is_configured,
        "telegram_configured": bool(self.telegram.app),
        "whatsapp_configured": bool(self.whatsapp and self.whatsapp.client),
        "last_delivery": last_delivery_timestamp,
        "delivery_errors_24h": error_count_24h
    }
```

---

## 8. Checklist de Implementación

### Fase 1: Email (1-2 días)

- [ ] Crear cuenta en Brevo
- [ ] Verificar dominio propio
- [ ] Configurar SPF/DKIM/DMARC
- [ ] Obtener credenciales SMTP
- [ ] Actualizar `.env.example`
- [ ] Configurar variables en hosting
- [ ] Test de envío local
- [ ] Test de envío en deploy
- [ ] Verificar llegada a inbox (no spam)
- [ ] Agregar logging de envíos

### Fase 2: Telegram (1 día)

- [ ] Crear bot con @BotFather
- [ ] Configurar `TELEGRAM_BOT_TOKEN` en hosting
- [ ] Verificar endpoint webhook
- [ ] Registrar webhook con Telegram
- [ ] Test `/start` en producción
- [ ] Test selección de categorías
- [ ] Test envío de brief
- [ ] Agregar rate limiting
- [ ] Monitorear errores

### Fase 3: Validación (1 semana)

- [ ] Crear 5 suscriptores de prueba
- [ ] Ejecutar 3 delivery cycles completos
- [ ] Verificar métricas en dashboard
- [ ] Revisar logs por errores
- [ ] Ajustar horarios de envío según feedback
- [ ] Documentar issues encontrados

### Fase 4: Lanzamiento Suave (2 semanas)

- [ ] Invitar 10-20 usuarios beta
- [ ] Recopilar feedback
- [ ] Ajustar frecuencia de emails
- [ ] Optimizar contenido de briefs
- [ ] Medir tasa de apertura (Brevo analytics)
- [ ] Iterar según métricas

---

## 9. Referencias

### Proveedores SMTP

- Brevo: https://www.brevo.com/pricing/
- Mailtrap: https://www.mailtrap.io/pricing/
- SendGrid: https://sendgrid.com/en-us/pricing

### Telegram Bot

- python-telegram-bot docs: https://docs.python-telegram-bot.org/
- Bot API: https://core.telegram.org/bots/api
- Webhook example: https://core.telegram.org/bots/api#setwebhook

### Email Deliverability

- SPF/DKIM/DMARC guide: https://www.mailchimp.com/resources/what-is-email-authentication/
- MX Toolbox (DNS check): https://mxtoolbox.com/
- Mail Tester (spam score): https://www.mail-tester.com/

---

## 10. Decisiones Pendientes

| Decisión | Opciones | Recomendación |
|----------|----------|---------------|
| **Proveedor SMTP** | Brevo vs Mailtrap vs SendGrid | Brevo (9,000/mes) |
| **Dominio email** | `@gmail.com` vs `@tudominio.com` | Dominio propio (credibilidad) |
| **Frecuencia de briefs** | 1x/día vs 2x/día vs 3x/semana | 1x/día (consistencia) |
| **Horario de envío** | Mañana vs Tarde vs Flexible | 9:00 AM La Paz (mañana laboral) |
| **Contenido del brief** | Top 5 vs Top 10 vs Personalizado | Top 5 (calidad > cantidad) |

---

*Documento creado para EcoBrief Bolivia. Actualizar conforme se implementen los canales.*
