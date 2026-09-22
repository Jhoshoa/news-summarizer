-- Guardar tambien CUANDO se observo el valor que quedo como referencia de
-- alerta, para que el aviso pueda decir "Referencia de las 11:32" (ver
-- src/db/price_alerts.py / PriceAlertNotifier). Nullable: las filas creadas
-- antes de esta migracion no tienen el dato y sus avisos se arman sin hora.
ALTER TABLE price_alert_state
    ADD COLUMN IF NOT EXISTS reference_collected_at TIMESTAMP;