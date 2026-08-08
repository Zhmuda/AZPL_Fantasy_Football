import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { getPlayers } from "../../api/players";
import { getTeams, getSeasons } from "../../api/fantasy";
import PlayerDetailModal from "../../components/PlayerDetailModal";
import s from "./PlayersPage.module.css";

const POSITIONS = [
  { key: "",  labelKey: "players.positions.all" },
  { key: "G", labelKey: "players.positions.G" },
  { key: "D", labelKey: "players.positions.D" },
  { key: "M", labelKey: "players.positions.M" },
  { key: "F", labelKey: "players.positions.F" },
];

const SORT_OPTIONS = [
  { key: "season_points",  labelKey: "common.sortPoints" },
  { key: "season_goals",   labelKey: "common.sortGoals" },
  { key: "season_assists", labelKey: "common.sortAssists" },
  { key: "price",          labelKey: "common.sortPrice" },
];

const PRICE_MAX_OPTIONS = [99, 5, 7, 9, 12];

export default function PlayersPage() {
  const { t } = useTranslation();
  const [players, setPlayers]     = useState([]);
  const [teams, setTeams]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [position, setPosition]   = useState("");
  const [teamId, setTeamId]       = useState("");
  const [maxPrice, setMaxPrice]   = useState(99);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch]       = useState("");
  const [sortBy, setSortBy]       = useState("season_points");
  const [detailId, setDetailId]   = useState(null);
  const [season, setSeason]       = useState(null);

  useEffect(() => { getTeams().then(setTeams); }, []);
  useEffect(() => {
    getSeasons().then(seasons => setSeason(seasons.find(sn => sn.is_active) ?? seasons[0]));
  }, []);

  // Дебаунс — без него каждый символ в поиске бил по /players отдельным запросом.
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (position) params.position = position;
      if (teamId)   params.team_id  = teamId;
      if (search)   params.search   = search;
      setPlayers(await getPlayers(params));
    } finally { setLoading(false); }
  }, [position, teamId, search]);

  useEffect(() => { load(); }, [load]);

  const sorted = [...players]
    .filter(p => p.price <= maxPrice)
    .sort((a, b) => b[sortBy] - a[sortBy]);

  return (
    <div className={s.page}>
      <div className={s.header}>
        <h1>{t("players.title")}</h1>
        <p className={s.sub}>{t("players.subtitle", { season: season?.name ?? "", count: sorted.length })}</p>
      </div>

      <div className={s.filters}>
        {/* Position */}
        <div className={s.posTabs}>
          {POSITIONS.map(p => (
            <button key={p.key}
              className={position === p.key ? s.posActive : s.posBtn}
              onClick={() => setPosition(p.key)}
            >{t(p.labelKey)}</button>
          ))}
        </div>

        {/* Club */}
        <select className={s.select} value={teamId} onChange={e => setTeamId(e.target.value)}>
          <option value="">{t("common.allClubs")}</option>
          {teams.map(tm => <option key={tm.id} value={tm.id}>{tm.name}</option>)}
        </select>

        {/* Max price */}
        <select className={s.select} value={maxPrice} onChange={e => setMaxPrice(Number(e.target.value))}>
          {PRICE_MAX_OPTIONS.map(v => (
            <option key={v} value={v}>{v === 99 ? t("common.anyPrice") : t("common.upTo", { price: v })}</option>
          ))}
        </select>

        {/* Sort */}
        <select className={s.select} value={sortBy} onChange={e => setSortBy(e.target.value)}>
          {SORT_OPTIONS.map(o => <option key={o.key} value={o.key}>{t(o.labelKey)}</option>)}
        </select>

        {/* Search */}
        <input className={s.search} placeholder={t("common.searchByName")}
          value={searchInput} onChange={e => setSearchInput(e.target.value)} />
      </div>

      {loading ? (
        <div className={s.empty}>{t("common.loading")}</div>
      ) : (
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("players.columns.rank")}</th>
                <th>{t("players.columns.player")}</th>
                <th>{t("players.columns.position")}</th>
                <th>{t("players.columns.club")}</th>
                <th title={t("players.columns.matchesTitle")}>{t("players.columns.matches")}</th>
                <th title={t("players.columns.goalsTitle")}>{t("players.columns.goals")}</th>
                <th title={t("players.columns.assistsTitle")}>{t("players.columns.assists")}</th>
                <th>{t("players.columns.points")}</th>
                <th>{t("players.columns.price")}</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p, i) => (
                <tr key={p.id} className={s.row} onClick={() => setDetailId(p.id)}>
                  <td className={s.rank}>{i + 1}</td>
                  <td className={s.name}>
                    {p.photo_url && (
                      <img src={p.photo_url} alt="" className={s.avatar}
                        onError={e => { e.target.style.display = "none"; }} />
                    )}
                    {p.name}
                  </td>
                  <td><span className={`pos-badge pos-${p.position}`}>{p.position}</span></td>
                  <td className={s.team}>{p.team?.name ?? t("common.dash")}</td>
                  <td className={s.stat}>{p.season_matches}</td>
                  <td className={s.stat}>{p.season_goals}</td>
                  <td className={s.stat}>{p.season_assists}</td>
                  <td className={s.pts}>{p.season_points}</td>
                  <td className={s.price}>£{p.price}m</td>
                </tr>
              ))}
            </tbody>
          </table>
          {sorted.length === 0 && <div className={s.empty}>{t("players.empty")}</div>}
        </div>
      )}

      <PlayerDetailModal playerId={detailId} onClose={() => setDetailId(null)} />
    </div>
  );
}
