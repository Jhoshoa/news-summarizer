ALTER TABLE subscribers
ADD COLUMN IF NOT EXISTS preferred_hour SMALLINT NOT NULL DEFAULT 9;

UPDATE subscribers
SET preferred_hour = CASE preferred_time
    WHEN 'manana' THEN 9
    WHEN 'tarde' THEN 16
    WHEN 'noche' THEN 20
    ELSE 9
END
WHERE preferred_time IS NOT NULL;

ALTER TABLE subscribers
ADD CONSTRAINT chk_subscribers_preferred_hour CHECK (preferred_hour BETWEEN 9 AND 23);

ALTER TABLE subscribers
DROP COLUMN IF EXISTS preferred_time;
