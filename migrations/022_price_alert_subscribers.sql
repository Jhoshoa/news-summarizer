-- Chats de Telegram suscriptos a las alertas de precio del bot separado
-- (PRICE_ALERT_BOT_TOKEN). Una fila por chat: /start agrega, /baja borra.
-- Es una tabla propia (no `subscribers` de noticias) porque son bots
-- distintos con propositos distintos -- ver src/db/price_alert_subscribers.py
-- y src/notifiers/price_alert_notifier.py.
CREATE TABLE IF NOT EXISTS price_alert_subscribers (
    telegram_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);