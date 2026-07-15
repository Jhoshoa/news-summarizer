# Configuración de Email con Brevo SMTP

**Última actualización:** 2026-07-15
**Proveedor:** Brevo (ex-Sendinblue)
**Tier:** Free Forever — 300 emails/día (~9,000/mes)

---

## Tabla de Contenidos

1. [Resumen de la Configuración](#1-resumen-de-la-configuración)
2. [Prerrequisitos](#2-prerrequisitos)
3. [Paso 1: Crear Cuenta en Brevo](#3-paso-1-crear-cuenta-en-brevo)
4. [Paso 2: Obtener Credenciales SMTP](#4-paso-2-obtener-credenciales-smtp)
5. [Paso 3: Autenticar Dominio (DKIM/DMARC)](#5-paso-3-autenticar-dominio)
6. [Paso 4: Configurar Variables de Entorno](#6-paso-4-configurar-variables-de-entorno)
7. [Paso 5: Configurar en Hostinger VPS](#7-paso-5-configurar-en-hostinger-vps)
8. [Pruebas](#8-pruebas)
9. [Riesgos y Mitigación](#9-riesgos-y-mitigación)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Resumen de la Configuración

| Parámetro | Valor |
|-----------|-------|
| SMTP Server | `smtp-relay.brevo.com` |
| SMTP Port | `587` (STARTTLS) o `465` (SSL) |
| SMTP Username | Tu email registrado en Brevo |
| SMTP Password | API Key de Brevo (NO API key general) |
| Free Tier | 300 emails/día, ~9,000/mes |
| Duración | **Free forever** (sin tarjeta de crédito) |

### Flujo de Configuración

```
Crear cuenta Brevo → Obtener SMTP Key → Autenticar dominio → Configurar .env → Probar
```

---

## 2. Prerrequisitos

- [ ] Dominio propio (ej: `ecobrief.com`)
- [ ] Acceso al panel DNS del dominio (Hostinger, Cloudflare, etc.)
- [ ] Python 3.11+ funcionando localmente
- [ ] Variables de entorno configuradas

---

## 3. Paso 1: Crear Cuenta en Brevo

1. Ir a https://www.brevo.com
2. Click **Sign up free**
3. Completar registro con email y contraseña
4. Verificar email (revisar bandeja de entrada)
5. Completar perfil de negocio

> **Nota:** El free tier no requiere tarjeta de crédito.

---

## 4. Paso 2: Obtener Credenciales SMTP

### 4.1 Ir a la página de SMTP

URL directa: https://app.brevo.com/settings/keys/smtp

### 4.2 Generar credenciales

1. En la pestaña **SMTP**, hacer click en **Generate a new SMTP key**
2. Dar un nombre descriptivo (ej: `ecobrief-production`)
3. Click **Generate**
4. **Copiar inmediatamente** la API Key generada (solo se muestra una vez)

### 4.3 Estructura de credenciales

```yaml
SMTP Server: smtp-relay.brevo.com
SMTP Port: 587 (recomendado) o 465
SMTP Username: tu-email@tudominio.com  # El email registrado en Brevo
SMTP Password: xsmtpsib-xxxxxxxxxxxx  # La API Key generada (prefijo xsmtpsib-)
```

> **IMPORTANTE:** Usar la SMTP Key, NO la API Key general de Brevo. La SMTP Key tiene el prefijo `xsmtpsib-`.

### 4.4 Verificar credenciales

1. Ir a https://app.brevo.com/settings/keys/smtp
2. Verificar que el email del remitente esté verificado
3. Si no está verificado, agregar y verificar el email

---

## 5. Paso 3: Autenticar Dominio

La autenticación del dominio es **crítica** para evitar que los emails lleguen a spam.

### 5.1 Ir a configuración de dominios

URL: https://app.brevo.com/senders/domain/list

### 5.2 Agregar dominio

1. Click **Add a domain**
2. Ingresar el dominio (ej: `ecobrief.com`)
3. Click **Add domain**

### 5.3 Autenticar automáticamente (Recomendado)

Brevo puede autenticar automáticamente si usas un proveedor de dominios compatible:

1. Seleccionar **Authenticate the domain automatically**
2. Click **Continue**
3. Iniciar sesión con tu proveedor de dominios (ej: Hostinger)
4. Brevo agregará los registros DNS automáticamente

### 5.4 Autenticar manualmente (Si automático no funciona)

Si la autenticación automática no está disponible, agregar manualmente estos registros DNS:

#### Registro 1: Brevo Code (TXT)

| Campo | Valor |
|-------|-------|
| Type | TXT |
| Name | `brevo` o `_brevo` (copiar de Brevo) |
| Value | `v=spf1 include:sendgrid.net ~all` (copiar exacto de Brevo) |
| TTL | 3600 (1 hora) |

#### Registro 2: DKIM (1 TXT o 2 CNAME)

**Opción A — 2 registros CNAME (recomendado):**

| Campo | DKIM 1 | DKIM 2 |
|-------|--------|--------|
| Type | CNAME | CNAME |
| Name | `s1._domainkey` (copiar de Brevo) | `s2._domainkey` (copiar de Brevo) |
| Value | `s1.domainkey.sendgrid.net` (copiar de Brevo) | `s2.domainkey.sendgrid.net` (copiar de Brevo) |
| TTL | 3600 | 3600 |

**Opción B — 1 registro TXT:**

| Campo | Valor |
|-------|-------|
| Type | TXT |
| Name | `default._domainkey` (copiar de Brevo) |
| Value | `v=DKIM1; k=rsa; p=MIGf...` (copiar exacto de Brevo) |
| TTL | 3600 |

#### Registro 3: DMARC (TXT)

| Campo | Valor |
|-------|-------|
| Type | TXT |
| Name | `_dmarc` |
| Value | `v=DMARC1; p=quarantine; rua=mailto:admin@tudominio.com` |
| TTL | 3600 |

> **Nota:** Reemplazar `admin@tudominio.com` con tu email real para recibir reportes.

### 5.5 Verificar autenticación

1. Volver a https://app.brevo.com/senders/domain/list
2. El dominio debería mostrar estado **Authenticated** (check verde)
3. Si no aparece, esperar hasta 24 horas para propagación DNS

### 5.6 Verificar con herramientas externas

```bash
# Verificar registros DNS (esperar propagación)
nslookup -type=TXT tudominio.com
nslookup -type=CNAME s1._domainkey.tudominio.com
nslookup -type=TXT _dmarc.tudominio.com

# O usar herramientas online:
# - https://mxtoolbox.com/DNSLookup.aspx
# - https://www.mail-tester.com/
```

---

## 6. Paso 4: Configurar Variables de Entorno

### 6.1 Variables para el archivo `.env`

```env
# ===========================================
# EMAIL - Brevo SMTP (Free Forever)
# ===========================================
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@tudominio.com
SMTP_PASSWORD=xsmtpsib-tu-api-key-aqui
SMTP_FROM_EMAIL=briefs@tudominio.com
SMTP_FROM_NAME=EcoBrief Bolivia
EMAIL_REQUIRE_VERIFICATION=false
```

### 6.2 Campos obligatorios vs opcionales

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `EMAIL_ENABLED` | Sí | `true` para activar envío |
| `SMTP_HOST` | Sí | Siempre `smtp-relay.brevo.com` |
| `SMTP_PORT` | Sí | `587` (STARTTLS) o `465` (SSL) |
| `SMTP_USERNAME` | Sí | Tu email registrado en Brevo |
| `SMTP_PASSWORD` | Sí | La SMTP Key de Brevo |
| `SMTP_FROM_EMAIL` | Sí | Email del remitente (debe estar verificado) |
| `SMTP_FROM_NAME` | No | Nombre del remitente (default: `EcoBrief Bolivia`) |
| `EMAIL_REQUIRE_VERIFICATION` | No | `false` para MVP |

### 6.3 Diferencia entre Local y Producción

| Campo | Local (.env) | Producción (VPS) |
|-------|-------------|-------------------|
| `SMTP_HOST` | `smtp-relay.brevo.com` | `smtp-relay.brevo.com` |
| `SMTP_PORT` | `587` | `587` |
| `SMTP_USERNAME` | Igual | Igual |
| `SMTP_PASSWORD` | Igual | Igual |
| `SMTP_FROM_EMAIL` | Igual | Igual |

> Las credenciales son las mismas en ambos ambientes.

### 6.4 Ejemplo completo para `.env.example`

```env
# ===========================================
# EMAIL - Brevo SMTP (Free Forever)
# Docs: https://help.brevo.com/hc/en-us/articles/7924908994450
# ===========================================
# 1. Crear cuenta en https://www.brevo.com
# 2. Obtener credenciales en https://app.brevo.com/settings/keys/smtp
# 3. Autenticar dominio en https://app.brevo.com/senders/domain/list
# 4. Free tier: 300 emails/día (~9,000/mes), sin tarjeta de crédito
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@tudominio.com
SMTP_PASSWORD=xsmtpsib-tu-api-key-aqui
SMTP_FROM_EMAIL=briefs@tudominio.com
SMTP_FROM_NAME=EcoBrief Bolivia
EMAIL_REQUIRE_VERIFICATION=false
```

---

## 7. Paso 5: Configurar en Hostinger VPS

### 7.1 Variables de entorno en el VPS

**Opción A: Editar archivo `.env` en el servidor**

```bash
# Conectar al VPS
ssh root@tu-ip-del-vps

# Navegar al directorio del proyecto
cd /var/www/news-summarizer  # O donde esté tu proyecto

# Editar .env
nano .env

# Agregar/actualizar variables EMAIL
EMAIL_ENABLED=true
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@tudominio.com
SMTP_PASSWORD=xsmtpsib-tu-api-key-aqui
SMTP_FROM_EMAIL=briefs@tudominio.com
SMTP_FROM_NAME=EcoBrief Bolivia
```

**Opción B: Variables de entorno en Docker Compose**

Si usas Docker, agregar en `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - EMAIL_ENABLED=true
      - SMTP_HOST=smtp-relay.brevo.com
      - SMTP_PORT=587
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL}
      - SMTP_FROM_NAME=EcoBrief Bolivia
```

**Opción C: Variables de entorno en panel de Hostinger**

Si usas el panel de Hostinger para Docker/containers:
1. Ir a **Docker** → **Containers**
2. Seleccionar tu container backend
3. Click **Settings** → **Environment Variables**
4. Agregar cada variable individualmente

### 7.2 Verificar que las variables se cargan

```bash
# Conectar al VPS
ssh root@tu-ip-del-vps

# Verificar variables (si el container está corriendo)
docker exec -it news-summarizer-backend-1 env | grep SMTP

# O ejecutar un script de prueba
docker exec -it news-summarizer-backend-1 python -c "
from src.config.settings import Settings
s = Settings()
print(f'EMAIL_ENABLED: {s.email_enabled}')
print(f'SMTP_HOST: {s.smtp_host}')
print(f'SMTP_PORT: {s.smtp_port}')
print(f'SMTP_USERNAME: {s.smtp_username}')
print(f'SMTP_FROM_EMAIL: {s.smtp_from_email}')
print(f'SMTP_PASSWORD: {\"***\" if s.smtp_password else \"NOT SET\"}')
"
```

### 7.3 Verificar conectividad SMTP desde el VPS

```bash
# Test de conexión SMTP desde el servidor
docker exec -it news-summarizer-backend-1 python -c "
import smtplib
try:
    with smtplib.SMTP('smtp-relay.brevo.com', 587, timeout=10) as smtp:
        smtp.starttls()
        smtp.login('tu-email@tudominio.com', 'tu-smtp-key')
        print('SMTP connection OK')
except Exception as e:
    print(f'SMTP connection FAILED: {e}')
"
```

### 7.4 Firewall — Abrir puerto de salida

El VPS necesita poder enviar por el puerto 587 (STARTTLS) y 465 (SSL). Verificar que no esté bloqueado:

```bash
# Verificar reglas de firewall (Ubuntu/Debian)
sudo ufw status

# Si el firewall está activo, el puerto de salida 587/465 debería estar abierto por defecto
# Solo necesitas bloquear ENTRADA, no salida
```

### 7.5 Configurar DNS del dominio desde Hostinger

Si el dominio está registrado en Hostinger:

1. Ir a https://hpanel.hostinger.com
2. Seleccionar dominio → **DNS / Nameservers**
3. Ir a **Manage DNS records**
4. Agregar registros TXT/CNAME según las instrucciones de Brevo (Paso 5)

#### Registros DNS para Hostinger

**Brevo Code (TXT):**
| Type | Name | Content | TTL |
|------|------|---------|-----|
| TXT | `brevo` | `v=spf1 include:sendgrid.net ~all` | Auto |

**DKIM (CNAME × 2):**
| Type | Name | Target | TTL |
|------|------|--------|-----|
| CNAME | `s1._domainkey` | `s1.domainkey.sendgrid.net` | Auto |
| CNAME | `s2._domainkey` | `s2.domainkey.sendgrid.net` | Auto |

**DMARC (TXT):**
| Type | Name | Content | TTL |
|------|------|---------|-----|
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:admin@tudominio.com` | Auto |

---

## 8. Pruebas

### 8.1 Prueba Local

```bash
# 1. Asegurar que .env tenga las credenciales correctas
cat .env | grep SMTP

# 2. Ejecutar test de email
python -c "
import asyncio
from src.distributors.email_handler import EmailHandler
from src.config.settings import Settings

settings = Settings()
handler = EmailHandler(settings=settings)

print(f'Configurado: {handler.is_configured}')

if handler.is_configured:
    result = asyncio.run(handler.send_message(
        to_email='tu-email-personal@gmail.com',
        subject='[EcoBrief] Test de configuración SMTP',
        body='Este es un email de prueba desde EcoBrief Bolivia.\n\nSi recibes este mensaje, la configuración SMTP está funcionando correctamente.'
    ))
    print(f'Enviado: {result}')
else:
    print('ERROR: SMTP no está configurado. Revisa las variables de entorno.')
"
```

### 8.2 Prueba en Producción (VPS)

```bash
# Conectar al VPS
ssh root@tu-ip-del-vps

# Ejecutar test dentro del container
docker exec -it news-summarizer-backend-1 python -c "
import asyncio
from src.distributors.email_handler import EmailHandler
from src.config.settings import Settings

settings = Settings()
handler = EmailHandler(settings=settings)

print(f'Configurado: {handler.is_configured}')

if handler.is_configured:
    result = asyncio.run(handler.send_message(
        to_email='tu-email-personal@gmail.com',
        subject='[EcoBrief] Test de producción SMTP',
        body='Este es un email de prueba desde EcoBrief Bolivia en PRODUCCIÓN.\n\nSi recibes este mensaje, la configuración SMTP está funcionando correctamente en el VPS.'
    ))
    print(f'Enviado: {result}')
else:
    print('ERROR: SMTP no está configurado en producción.')
"
```

### 8.3 Prueba End-to-End (API)

```bash
# Crear suscriptor y enviar brief
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tu-email@gmail.com",
    "categories": ["economia", "politica"]
  }'

# Trigger delivery
curl -X POST http://localhost:8000/trigger/delivery \
  -H "Authorization: Bearer tu-api-key"

# Verificar recepción del email
```

### 8.4 Verificar deliverability

1. Enviar email de prueba a https://www.mail-tester.com/
2. Copiar la dirección temporal que te dan
3. Enviar el email desde EcoBrief a esa dirección
4. Verificar el score (debería ser 9+/10)
5. Revisar si hay problemas de:
   - SPF
   - DKIM
   - DMARC
   - Contenido de spam

---

## 9. Riesgos y Mitigación

### 9.1 Riesgos Críticos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Email llega a spam** | Alta | Alto | Configurar SPF/DKIM/DMARC correctamente; usar dominio propio; warmup gradual |
| **Credenciales comprometidas** | Baja | Crítico | Usar SMTP Key (no API Key); rotar periódicamente; nunca en logs |
| **Rate limit de Brevo** | Baja | Medio | 300/día es suficiente para MVP; monitorear uso |
| **Dominio no autenticado** | Media | Alto | Verificar estado en Brevo; usar autenticación automática |

### 9.2 Riesgos Operacionales

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Variables faltantes en deploy** | Alta | Crítico | Checklist de deploy; test de salud al startup |
| **Timeout de conexión** | Baja | Medio | Timeout de 20s en código; retry con backoff |
| **Servidor Brevo caído** | Muy baja | Alto | Monitorear status.brevo.com; fallback a otro proveedor |
| **Emails rebotados** | Media | Medio | Monitorear bounces; limpiar lista periódicamente |

### 9.3 Warmup de Dominio (Semana 1)

Para nuevos dominios, incrementar gradualmente el volumen:

| Día | Emails/día | Total |
|-----|------------|-------|
| 1-2 | 50 | 100 |
| 3-4 | 100 | 200 |
| 5-6 | 200 | 400 |
| 7+ | 300 | Full capacity |

> **Nota:** Brevo ya tiene IPs pre-calentados, así que el warmup es menos agresivo que con otros proveedores.

### 9.4 Prevención de Spam

```
1. SPF: Configurar registros DNS correctamente
2. DKIM: Firmar digitalmente los emails
3. DMARC: Politica quarantine/reject para protección
4. Contenido: Incluir enlace de baja; evitar palabras de spam
5. Frecuencia: Máximo 1 email/día por suscriptor
6. Reputación: Monitorear métricas de Brevo regularmente
```

---

## 10. Troubleshooting

### 10.1 Error: "SMTP no configurado"

**Causa:** Variables de entorno no cargadas o incompletas.

**Solución:**
```bash
# Verificar que todas las variables estén presentes
env | grep SMTP
env | grep EMAIL

# Verificar que EMAIL_ENABLED=true
echo $EMAIL_ENABLED
```

### 10.2 Error: "Connection refused" o timeout

**Causa:** Firewall bloqueando puerto 587/465 o DNS no resuelve.

**Solución:**
```bash
# Verificar resolución DNS
nslookup smtp-relay.brevo.com

# Verificar conectividad
telnet smtp-relay.brevo.com 587

# Verificar que STARTTLS funcione
openssl s_client -connect smtp-relay.brevo.com:587 -starttls smtp
```

### 10.3 Error: "Authentication failed"

**Causa:** Credenciales incorrectas o usando API Key en lugar de SMTP Key.

**Solución:**
1. Verificar que estás usando la SMTP Key (prefijo `xsmtpsib-`)
2. Regenerar SMTP Key en https://app.brevo.com/settings/keys/smtp
3. Verificar que el email del username coincida con el registrado en Brevo

### 10.4 Error: "Sender address rejected"

**Causa:** Email del remitente no está verificado en Brevo.

**Solución:**
1. Ir a https://app.brevo.com/senders
2. Verificar que el email esté listado y verificado
3. Si no está, agregarlo y verificar el enlace de confirmación

### 10.5 Emails llegan a spam

**Causa:** Dominio no autenticado o reputación baja.

**Solución:**
1. Verificar autenticación del dominio en Brevo (status: Authenticated)
2. Ejecutar test en https://www.mail-tester.com/
3. Verificar registros SPF/DKIM/DMARC con https://mxtoolbox.com/
4. Revisar contenido del email (palabras de spam, links sospechosos)

### 10.6 Emails no llegan en producción

**Causa:** Variables de entorno diferentes entre local y producción.

**Solución:**
```bash
# Comparar variables local vs producción
# Local:
cat .env | grep SMTP

# Producción (en el VPS):
docker exec -it news-summarizer-backend-1 env | grep SMTP

# Verificar que coincidan exactamente
```

---

## Referencias Oficiales de Brevo

| Recurso | URL |
|---------|-----|
| SMTP Relay Setup | https://help.brevo.com/hc/en-us/articles/7924908994450 |
| Domain Authentication | https://help.brevo.com/hc/en-us/articles/12163873383186 |
| Developer Docs SMTP | https://developers.brevo.com/docs/smtp-integration |
| SMTP Keys Management | https://app.brevo.com/settings/keys/smtp |
| Domain Settings | https://app.brevo.com/senders/domain/list |
| SMTP Ports Guide | https://help.brevo.com/hc/en-us/articles/10905415650322 |
| IP Ranges (B2B) | https://help.brevo.com/hc/en-us/articles/208848409 |
| Troubleshooting SMTP | https://help.brevo.com/hc/en-us/articles/115000188150 |
| Status Page | https://status.brevo.com/ |

---

## Checklist Pre-Deploy

- [ ] Cuenta Brevo creada y verificada
- [ ] SMTP Key generada (prefijo `xsmtpsib-`)
- [ ] Dominio agregado en Brevo
- [ ] Dominio autenticado (DKIM/DMARC/SPF)
- [ ] Email del remitente verificado en Brevo
- [ ] Variables `.env` actualizadas con credenciales Brevo
- [ ] Test local exitoso
- [ ] Variables configuradas en VPS/hosting
- [ ] Test en producción exitoso
- [ ] Test en https://www.mail-tester.com/ (score 9+)
- [ ] Verificar que emails llegan a inbox (no spam)
- [ ] Logging de envíos configurado
- [ ] Monitoreo de métricas activo

---

*Documento creado para EcoBrief Bolivia. Basado en documentación oficial de Brevo (2026).*
