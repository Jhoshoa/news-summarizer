-- Una fila por indicator_code: el ultimo valor que disparo una alerta de
-- precio (PriceAlertNotifier). El chequeo de umbral compara siempre contra
-- esta referencia, no contra la corrida anterior ni una ventana fija --
-- ver src/db/price_alerts.py.
CREATE TABLE IF NOT EXISTS price_alert_state (
    indicator_code VARCHAR(160) PRIMARY KEY,
    reference_value NUMERIC(18, 6) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
