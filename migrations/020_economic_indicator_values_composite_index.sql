-- get_history() filtra por indicator_code IN (...) AND collected_at >= :since,
-- y ordena por collected_at -- con indices separados en cada columna,
-- Postgres solo puede aprovechar bien uno de los dos (o combinarlos con un
-- bitmap AND, mas caro) y ademas tiene que ordenar el resultado aparte. Un
-- indice compuesto en el mismo orden que la consulta cubre el filtro y el
-- ORDER BY de una sola pasada.
CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_code_collected_at
ON economic_indicator_values (indicator_code, collected_at);
