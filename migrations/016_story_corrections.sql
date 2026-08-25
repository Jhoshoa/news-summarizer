-- Fase 2.5: historial de correcciones. Marcar una historia como corregida
-- activa la etiqueta de confianza "corrected" (story_confidence.py), que ya
-- estaba lista pero inalcanzable hasta ahora.
CREATE TABLE IF NOT EXISTS story_corrections (
    id BIGSERIAL PRIMARY KEY,
    story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
    reason TEXT NOT NULL,
    corrected_by VARCHAR(120) NULL,
    corrected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_story_corrections_story_id
ON story_corrections(story_id);
