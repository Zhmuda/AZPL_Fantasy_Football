import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { getPlayer, getPlayerMatches } from "../api/players";
import s from "./PlayerDetailModal.module.css";

export default function PlayerDetailModal({ playerId, onClose }) {
  const { t } = useTranslation();
  const [player, setPlayer] = useState(null);
  const [matches, setMatches] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!playerId) return;
    setPlayer(null);
    setMatches(null);
    setLoading(true);
    Promise.all([getPlayer(playerId), getPlayerMatches(playerId)])
      .then(([p, m]) => { setPlayer(p); setMatches(m); })
      .finally(() => setLoading(false));
  }, [playerId]);

  useEffect(() => {
    if (!playerId) return;
    const onKey = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [playerId, onClose]);

  if (!playerId) return null;

  return (
    <div className={s.overlay} onClick={onClose}>
      <div className={s.modal} onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <button className={s.closeBtn} onClick={onClose} aria-label={t("playerDetail.close")}>✕</button>

        {loading || !player ? (
          <div className={s.loading}>{t("common.loading")}</div>
        ) : (
          <>
            <div className={s.header}>
              {player.photo_url && (
                <img src={player.photo_url} alt="" className={s.avatar}
                  onError={e => { e.target.style.display = "none"; }} />
              )}
              <div>
                <h2 className={s.name}>{player.name}</h2>
                <div className={s.meta}>
                  <span className={`pos-badge pos-${player.position}`}>{player.position}</span>
                  {" "}{player.team?.name ?? t("common.dash")} · £{player.price}m
                  {player.is_active === false && (
                    <span className={s.inactiveTag}> · {t("myTeam.bench.inactiveTag")}</span>
                  )}
                </div>
              </div>
            </div>

            <div className={s.statsRow}>
              <div className={s.stat}>
                <div className={s.statVal}>{player.season_points}</div>
                <div className={s.statLabel}>{t("players.columns.points")}</div>
              </div>
              <div className={s.stat}>
                <div className={s.statVal}>{player.season_goals}</div>
                <div className={s.statLabel}>{t("players.columns.goals")}</div>
              </div>
              <div className={s.stat}>
                <div className={s.statVal}>{player.season_assists}</div>
                <div className={s.statLabel}>{t("players.columns.assists")}</div>
              </div>
              <div className={s.stat}>
                <div className={s.statVal}>{player.season_matches}</div>
                <div className={s.statLabel}>{t("players.columns.matches")}</div>
              </div>
            </div>

            <div className={s.historyTitle}>{t("playerDetail.recentMatches")}</div>
            {matches && matches.length === 0 && (
              <div className={s.empty}>{t("playerDetail.noMatches")}</div>
            )}
            {matches && matches.length > 0 && (
              <div className={s.historyList}>
                {matches.map(m => (
                  <div key={m.match_id} className={s.historyRow}>
                    <div className={s.historyOpp}>
                      {m.is_home ? "" : "@ "}{m.opponent}
                      {m.round_number != null && (
                        <span className={s.historyRound}> · {t("myTeam.round", { number: m.round_number })}</span>
                      )}
                    </div>
                    <div className={s.historyScore}>{m.home_score}–{m.away_score}</div>
                    <div className={s.historyPts}>{m.fantasy_points} {t("myTeam.playerCard.points")}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
