CREATE TABLE IF NOT EXISTS worldcup_matches (
    id SERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    match_time TIME NOT NULL,
    group_name VARCHAR(2) NOT NULL,
    home_team VARCHAR(50) NOT NULL,
    away_team VARCHAR(50) NOT NULL,
    home_flag VARCHAR(20),
    away_flag VARCHAR(20),
    home_score INTEGER,
    away_score INTEGER,
    is_playing BOOLEAN DEFAULT FALSE,
    is_finished BOOLEAN DEFAULT FALSE,
    stage VARCHAR(20) NOT NULL DEFAULT 'group',
    venue VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_worldcup_matches_date ON worldcup_matches(match_date);
