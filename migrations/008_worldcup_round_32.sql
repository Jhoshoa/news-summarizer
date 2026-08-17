INSERT INTO worldcup_matches (
    match_date,
    match_time,
    group_name,
    home_team,
    away_team,
    home_flag,
    away_flag,
    stage,
    venue
)
SELECT
    v.match_date::date,
    v.match_time::time,
    v.group_name,
    v.home_team,
    v.away_team,
    v.home_flag,
    v.away_flag,
    v.stage,
    v.venue
FROM (VALUES
-- Dom 28 jun
('2026-06-28', '15:00', 'KO', 'Sudáfrica', 'Canadá',       '🇿🇦', '🇨🇦', 'round_32', 'Los Angeles Stadium'),
-- Lun 29 jun
('2026-06-29', '13:00', 'KO', 'Brasil',      'Japón',       '🇧🇷', '🇯🇵', 'round_32', 'Houston Stadium'),
('2026-06-29', '16:30', 'KO', 'Alemania',    'Paraguay',    '🇩🇪', '🇵🇾', 'round_32', 'Boston Stadium'),
('2026-06-29', '21:00', 'KO', 'Países Bajos', 'Marruecos',  '🇳🇱', '🇲🇦', 'round_32', 'Estadio Monterrey'),
-- Mar 30 jun
('2026-06-30', '13:00', 'KO', 'Costa de Marfil', 'Noruega', '🇨🇮', '🇳🇴', 'round_32', 'Dallas Stadium'),
('2026-06-30', '17:00', 'KO', 'Francia',    'Suecia',      '🇫🇷', '🇸🇪', 'round_32', 'New York New Jersey Stadium'),
('2026-06-30', '21:00', 'KO', 'México',     'Ecuador',     '🇲🇽', '🇪🇨', 'round_32', 'Estadio Ciudad de México'),
-- Mié 1 jul
('2026-07-01', '12:00', 'KO', 'Inglaterra',        'RD Congo',           '🏴󠁧󠁢󠁥󠁮󠁧󠁿', '🇨🇩', 'round_32', 'Atlanta Stadium'),
('2026-07-01', '16:00', 'KO', 'Bélgica',           'Senegal',            '🇧🇪', '🇸🇳', 'round_32', 'Seattle Stadium'),
('2026-07-01', '20:00', 'KO', 'Estados Unidos',    'Bosnia y Herzegovina', '🇺🇸', '🇧🇦', 'round_32', 'San Francisco Bay Area Stadium'),
-- Jue 2 jul
('2026-07-02', '15:00', 'KO', 'España',  'Austria',   '🇪🇸', '🇦🇹', 'round_32', 'Los Angeles Stadium'),
('2026-07-02', '19:00', 'KO', 'Portugal', 'Croacia',  '🇵🇹', '🇭🇷', 'round_32', 'Toronto Stadium'),
('2026-07-02', '23:00', 'KO', 'Suiza',   'Argelia',  '🇨🇭', '🇩🇿', 'round_32', 'BC Place Vancouver'),
-- Vie 3 jul
('2026-07-03', '14:00', 'KO', 'Australia',  'Egipto',   '🇦🇺', '🇪🇬', 'round_32', 'Dallas Stadium'),
('2026-07-03', '18:00', 'KO', 'Argentina',  'Cabo Verde', '🇦🇷', '🇨🇻', 'round_32', 'Miami Stadium'),
('2026-07-03', '21:30', 'KO', 'Colombia',   'Ghana',    '🇨🇴', '🇬🇭', 'round_32', 'Kansas City Stadium')
) AS v(
    match_date,
    match_time,
    group_name,
    home_team,
    away_team,
    home_flag,
    away_flag,
    stage,
    venue
)
WHERE NOT EXISTS (
    SELECT 1
    FROM worldcup_matches existing
    WHERE existing.match_date = v.match_date::date
      AND existing.match_time = v.match_time::time
      AND existing.home_team = v.home_team
      AND existing.away_team = v.away_team
      AND existing.stage = v.stage
);