import { PanelSkeleton } from "../ui/Skeleton";
import { useGetWorldCupMatchesQuery } from "../../services/api";

const MAX_VISIBLE = 4;

const groupLabels: Record<string, string> = {
  A: "Grupo A", B: "Grupo B", C: "Grupo C", D: "Grupo D",
  E: "Grupo E", F: "Grupo F", G: "Grupo G", H: "Grupo H",
  I: "Grupo I", J: "Grupo J", K: "Grupo K", L: "Grupo L",
};

const formatMatchTime = (time: string) => {
  const [h, m] = time.split(":");
  return `${h}:${m}`;
};

const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const formatDateShort = (dateStr: string) => {
  const [y, m, d] = dateStr.split("-");
  const months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  return `${parseInt(d)} ${months[parseInt(m) - 1]}`;
};

export const WorldCupPanel = () => {
  const today = todayStr();
  const { data: allMatches, isFetching } = useGetWorldCupMatchesQuery();

  if (isFetching) {
    return <PanelSkeleton />;
  }

  if (!allMatches || allMatches.length === 0) {
    return null;
  }

  const todayMatches = allMatches.filter((m) => m.match_date === today);

  if (todayMatches.length === 0) {
    return null;
  }

  const upcoming = allMatches.filter((m) => m.match_date > today);

  const visible = todayMatches.length >= MAX_VISIBLE
    ? todayMatches
    : [...todayMatches, ...upcoming.slice(0, MAX_VISIBLE - todayMatches.length)];

  return (
    <section className="worldcup-panel">
      <div className="worldcup-header">
        <span className="worldcup-icon">🏆</span>
        <span className="section-label">Mundial 2026 — Partidos de hoy</span>
      </div>
      <div className="worldcup-matches">
        {visible.map((m) => {
          const isLive = m.is_playing;
          const isFinished = m.is_finished;
          const isToday = m.match_date === today;
          const showScore = isLive || isFinished || (m.home_score != null && m.away_score != null);
          const card = (
            <>
              <div className="worldcup-teams">
                <span className="worldcup-team">
                  {m.home_flag && <span className="worldcup-flag">{m.home_flag}</span>}
                  <span className="worldcup-team-name">{m.home_team}</span>
                </span>
                <span className="worldcup-vs">
                  {showScore ? (
                    <span className="worldcup-score">
                      {m.home_score ?? 0} – {m.away_score ?? 0}
                    </span>
                  ) : (
                    <span className="worldcup-vs-text">vs</span>
                  )}
                </span>
                <span className="worldcup-team">
                  <span className="worldcup-team-name">{m.away_team}</span>
                  {m.away_flag && <span className="worldcup-flag">{m.away_flag}</span>}
                </span>
              </div>
              <div className="worldcup-meta">
                <span className="worldcup-venue">{m.venue}</span>
                <span className="worldcup-time">{formatMatchTime(m.match_time)}</span>
                <span className="worldcup-group">{groupLabels[m.group] || m.group}</span>
              </div>
              {!isToday && <span className="worldcup-date-tiny">{formatDateShort(m.match_date)}</span>}
              {isLive && <span className="worldcup-live-badge">EN VIVO</span>}
            </>
          );

          return isLive ? (
            <a
              key={m.id}
              href="https://futbol-libres.su/"
              target="_blank"
              rel="noopener noreferrer"
              className={`worldcup-match live ${isFinished ? "finished" : ""}`}
            >
              {card}
            </a>
          ) : (
            <div
              key={m.id}
              className={`worldcup-match ${isFinished ? "finished" : ""}`}
            >
              {card}
            </div>
          );
        })}
      </div>
    </section>
  );
};
