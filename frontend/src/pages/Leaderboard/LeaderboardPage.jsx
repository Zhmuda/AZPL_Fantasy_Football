import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { getSeasons, getLeaderboard } from "../../api/fantasy";
import s from "./LeaderboardPage.module.css";

const PAGE_SIZE = 10;

export default function LeaderboardPage() {
  const { t } = useTranslation();
  const [rows, setRows]       = useState([]);
  const [season, setSeason]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(0);

  useEffect(() => {
    getSeasons().then(seasons => {
      const active = seasons.find(s => s.is_active) ?? seasons[0];
      if (active) { setSeason(active); load(active.id); }
      else setLoading(false);
    });
  }, []);

  const load = (id) => {
    setLoading(true);
    setPage(0);
    getLeaderboard(id)
      .then(setRows)
      .finally(() => setLoading(false));
  };

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages - 1);
  const pageRows = rows.slice(currentPage * PAGE_SIZE, currentPage * PAGE_SIZE + PAGE_SIZE);

  const medals = ["🥇", "🥈", "🥉"];

  return (
    <div className={s.page}>
      <div className={s.header}>
        <h1>{t("leaderboard.title")}</h1>
        {season && <p className={s.sub}>{season.name}</p>}
      </div>

      {loading ? (
        <div className={s.loading}>{t("common.loading")}</div>
      ) : rows.length === 0 ? (
        <div className={s.empty}>
          <p>{t("leaderboard.empty")}</p>
          <small>{t("leaderboard.emptyHint")}</small>
        </div>
      ) : (
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("leaderboard.columns.rank")}</th>
                <th>{t("leaderboard.columns.team")}</th>
                <th>{t("leaderboard.columns.manager")}</th>
                <th>{t("leaderboard.columns.points")}</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <tr key={row.rank} className={row.rank <= 3 ? s.top : ""}>
                  <td className={s.rank}>
                    {medals[row.rank - 1] ?? row.rank}
                  </td>
                  <td className={s.teamName}>{row.team_name}</td>
                  <td className={s.manager}>@{row.username}</td>
                  <td className={s.pts}>{row.total_points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && rows.length > 0 && totalPages > 1 && (
        <div className={s.pagination}>
          <button
            className={s.pageBtn}
            disabled={currentPage === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
          >
            {t("players.pagination.prev")}
          </button>
          <span className={s.pageInfo}>
            {t("players.pagination.page", { current: currentPage + 1, total: totalPages })}
          </span>
          <button
            className={s.pageBtn}
            disabled={currentPage >= totalPages - 1}
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
          >
            {t("players.pagination.next")}
          </button>
        </div>
      )}
    </div>
  );
}
