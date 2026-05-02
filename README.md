# News Summarizer Bolivia 🇧🇴

Resume automático de noticias diarias de Bolivia con IA. Envía resúmenes a tus usuarios por WhatsApp y Telegram.

## Características

- 🌐 **Web Scraping**: Recopila noticias de medios bolivianos (Radio Fides, Unitel, Red Uno, Red Bolívar)
- 🤖 **IA**: Resume y clasifica noticias con Groq/OpenAI
- 📱 **Multi-canal**: Envía por WhatsApp (Twilio) y Telegram
- ⚙️ **Configurable**: Usuarios eligen sus categorías preferidas
- ⏰ **Programable**: Envíos automáticos mañana y tarde
- 🏷️ **Categorías**: Economía, Política, Deportes, Tecnología, Entretenimiento

## Requisitos

- Python 3.11+
- PostgreSQL (opcional, para producción)
- API keys (Groq gratis o OpenAI)

## Instalación

### 1. Clonar y crear entorno virtual

```bash
# En Linux/Mac
python -m venv venv
source venv/bin/activate

# En Windows
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Instalar Playwright (para scraping)

```bash
playwright install
playwright install-deps
```

> **¿Por qué no está en requirements.txt?** Son comandos shell, no paquetes pip:
> - `playwright install` descarga ~100MB por navegador
> - Solo se necesita ejecutar una vez
> - Varía según el sistema operativo

### 4. Configurar variables de entorno

```bash
copy .env.example .env
```

Edita el archivo `.env` con tus API keys:

```env
# ===========================================
# LLM - IA (Groq gratis)
# ===========================================
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_api_key_aqui

# News API (opcional, como backup)
NEWS_API_KEY=tu_newsapi_key

# ===========================================
# WhatsApp - Twilio (opcional)
# ===========================================
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=whatsapp:+...

# ===========================================
# Telegram (opcional)
# ===========================================
TELEGRAM_BOT_TOKEN=tu_bot_token

# ===========================================
# Base de datos (opcional)
# ===========================================
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/news_summarizer
```

## Obtener API Keys

### Groq (Gratis - Recomendado para inicio)

1. Ve a https://console.groq.com/
2. Regístrate (no requiere tarjeta)
3. Crea una API key en "API Keys"
4. Copia la key: `gsk_...`

### NewsAPI (Opcional - Backup)

1. Ve a https://newsapi.org/
2. Regístrate gratis
3. Copia tu API key

### Twilio WhatsApp (Opcional)

1. Ve a https://www.twilio.com/whatsapp
2. Crea un proyecto
3. Obtiene Account SID, Auth Token y Phone Number

### Telegram Bot

1. Abre @BotFather en Telegram
2. Envía `/newbot`
3. Copia el token

## Ejecutar

### Desarrollo

```bash
python -m src.main
```

O con uvicorn (auto-reload):

```bash
uvicorn src.main:app --reload
```

El servidor estará en: http://localhost:8000

### Producción

```bash
# Con gunicorn
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker

# O con Docker
docker-compose up -d
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|---------|-----------|
| GET | `/` | Estado de la app |
| GET | `/health` | Health check |
| GET | `/stats` | Estadísticas |
| POST | `/trigger/summary` | Enviar resúmenes manualmente |
| POST | `/webhook/whatsapp` | Webhook Twilio |

## Comandos

### Trigger manual de resumen

```bash
curl -X POST "http://localhost:8000/trigger/summary?time_of_day=morning"
```

### Ver estadísticas

```bash
curl "http://localhost:8000/stats"
```

## Configuración de Usuarios

### WhatsApp

El usuario envía:
- `Hola` → Menú de categorías
- `1,2,3` → Seleccionar categorías
- `6` → Todas
- `/preferencias` → Cambiar
- `/cancelar` → Darse de baja

### Telegram

El usuario envía:
- `/start` → Iniciar
- `/preferencias` → Menú de categorías
- `/cancelar` → Darse de baja

## Estructura del Proyecto

```
news-summarizer/
├── src/
│   ├── config/          # Configuración
│   ├── collectors/     # NewsAPI + Scraping
│   ├── processors/    # Deduplicación, Clasificación, Ranking, Resumen
│   ├── distributors/ # WhatsApp, Telegram
│   ├── db/          # Base de datos
│   ├── scheduler/    # Jobs programados
│   ├── llm          # Cliente IA
│   └── main.py       # Entry point
├── config/
│   └── sources.yaml  # Fuentes de noticias
├── tests/
├── requirements.txt
└── .env
```

## Agregar Nuevas Fuentes

Edita `config/sources.yaml`:

```yaml
sources:
  - name: "MiNuevoMedio"
    url: "https://www.misitio.com/"
    category: "general"
    selector: "article"
    title_selector: "h2 a"
    url_selector: "a"
    enabled: true
```

## Resolución de Problemas

### "Playwright no está instalado"

```bash
pip install playwright
playwright install chromium
```

### "Groq API key inválida"

Verifica que la key tenga el formato `gsk_...` y esté en el archivo `.env`.

### "No hay noticias"

- Verifica que los sitios estén accesibles
- Revisa los logs en `logs/`
- Intenta primero con NewsAPI (más confiable)

### "Twilio no envía mensajes"

- Verifica Account SID, Auth Token y Phone Number
- Asegúrate que el número esté verificado en Twilio

## Variables de Entorno Completas

```env
# ===========================================
# GENERAL
# ===========================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# ===========================================
# LLM
# ===========================================
LLM_PROVIDER=groq
GROQ_API_KEY=
OPENAI_API_KEY=

# ===========================================
# NEWS
# ===========================================
NEWS_API_KEY=
NEWS_API_COUNTRY=bo
NEWS_API_LANGUAGE=es

# ===========================================
# SCRAPER
# ===========================================
SCRAPER_ENABLED=true
SCRAPER_SOURCES=radiofides,unitel,reduno,redbolivision
SCRAPER_TIMEOUT=30

# ===========================================
# WHATSAPP
# ===========================================
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# ===========================================
# TELEGRAM
# ===========================================
TELEGRAM_BOT_TOKEN=

# ===========================================
# DB
# ===========================================
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/news_summarizer

# ===========================================
# SCHEDULER
# ===========================================
SCHEDULE_TIMEZONE=America/La_Paz
SCHEDULE_SUMMARY_MORNING=08:00
SCHEDULE_SUMMARY_EVENING=18:00
```

## Costos Estimados

| Componente | Desarrollo | Producción |
|-----------|-----------|-----------|
| Groq | $0 | $5-10/mes |
| NewsAPI | $0 | $15/mes |
| Twilio | $0 | $5-15/mes |
| Hosting | $0* | $10-20/mes |
| **Total** | **$0** | **$35-60/mes** |

*Railway, Vercel, Render tienen tier gratuito

## Contributing

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva`)
3. Commit (`git commit -am 'Agrega...'`)
4. Push (`git push origin feature/nueva`)
5. Crea un Pull Request

## Licencia

MIT License - libre para usar y modificar.