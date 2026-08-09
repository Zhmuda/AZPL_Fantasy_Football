import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { getSeasons } from "../../api/fantasy";
import { getMyLeagues, createLeague, joinLeague, getLeagueStandings, leaveLeague } from "../../api/leagues";
import s from "./LeaguesPage.module.css";

export default function LeaguesPage() {
  const { t } = useTranslation();
  const [season, setSeason]     = useState(null);
  const [leagues, setLeagues]   = useState([]);
  const [loading, setLoading]   = useState(true);

  const [name, setName]         = useState("");
  const [code, setCode]         = useState("");
  const [creating, setCreating] = useState(false);
  const [joining, setJoining]   = useState(false);
  const [formError, setFormError] = useState("");

  const [selected, setSelected]   = useState(null); // league id
  const [standings, setStandings] = useState(null);
  const [standingsLoading, setStandingsLoading] = useState(false);
  const [copied, setCopied]       = useState(false);

  const loadLeagues = useCallback((seasonId) => {
    setLoading(true);
    getMyLeagues(seasonId).then(setLeagues).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    getSeasons().then(seasons => {
      const active = seasons.find(x => x.is_active) ?? seasons[0];
      if (active) { setSeason(active); loadLeagues(active.id); }
      else setLoading(false);
    });
  }, [loadLeagues]);

  const submitCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) { setFormError(t("leagues.errors.nameRequired")); return; }
    setFormError(""); setCreating(true);
    try {
      const league = await createLeague(name.trim(), season.id);
      setLeagues(prev => [league, ...prev]);
      setName("");
    } catch (err) {
      setFormError(err.response?.data?.detail ?? t("leagues.errors.generic"));
    } finally {
      setCreating(false);
    }
  };

  const submitJoin = async (e) => {
    e.preventDefault();
    if (!code.trim()) { setFormError(t("leagues.errors.codeRequired")); return; }
    setFormError(""); setJoining(true);
    try {
      const league = await joinLeague(code.trim());
      setLeagues(prev => prev.some(l => l.id === league.id) ? prev : [league, ...prev]);
      setCode("");
    } catch (err) {
      setFormError(err.response?.data?.detail ?? t("leagues.errors.generic"));
    } finally {
      setJoining(false);
    }
  };

  const openLeague = (id) => {
    setSelected(id);
    setStandings(null);
    setStandingsLoading(true);
    getLeagueStandings(id).then(setStandings).finally(() => setStandingsLoading(false));
  };

  const backToList = () => { setSelected(null); setStandings(null); };

  const doLeave = async () => {
    if (!standings) return;
    if (!window.confirm(t("leagues.leaveConfirm", { name: standings.league.name }))) return;
    await leaveLeague(standings.league.id);
    setLeagues(prev => prev.filter(l => l.id !== standings.league.id));
    backToList();
  };

  const copyCode = (leagueCode) => {
    navigator.clipboard?.writeText(leagueCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (loading) return <div className={s.centered}><div className={s.spinner} /></div>;

  if (selected) {
    return (
      <div className={s.page}>
        <button className={s.backBtn} onClick={backToList}>{t("leagues.backBtn")}</button>

        {standingsLoading || !standings ? (
          <div className={s.loading}>{t("common.loading")}</div>
        ) : (
          <>
            <div className={s.header}>
              <div>
                <h1>{standings.league.name}</h1>
                <p className={s.sub}>{t("leagues.members", { count: standings.league.member_count })}</p>
              </div>
              <div className={s.codeBox}>
                <span className={s.codeLabel}>{t("leagues.code")}</span>
                <div className={s.codeRow}>
                  <code className={s.codeVal}>{standings.league.code}</code>
                  <button className={s.copyBtn} onClick={() => copyCode(standings.league.code)}>
                    {copied ? t("leagues.copied") : t("leagues.copyBtn")}
                  </button>
                </div>
              </div>
            </div>

            <div className={s.tableWrap}>
              <table className={s.table}>
                <thead>
                  <tr>
                    <th>{t("leagues.columns.rank")}</th>
                    <th>{t("leagues.columns.manager")}</th>
                    <th>{t("leagues.columns.team")}</th>
                    <th>{t("leagues.columns.points")}</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.standings.map(row => (
                    <tr key={row.user_id} className={row.is_me ? s.me : ""}>
                      <td className={s.rank}>{row.rank}</td>
                      <td className={s.manager}>@{row.username}</td>
                      <td className={s.teamName}>
                        {row.team_name ?? <span className={s.noTeam}>{t("leagues.noTeamYet")}</span>}
                      </td>
                      <td className={s.pts}>{row.total_points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button className={s.leaveBtn} onClick={doLeave}>{t("leagues.leaveBtn")}</button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={s.page}>
      <div className={s.header}>
        <div>
          <h1>{t("leagues.title")}</h1>
          <p className={s.sub}>{t("leagues.subtitle")}</p>
        </div>
      </div>

      <div className={s.formsRow}>
        <form className={s.formCard} onSubmit={submitCreate}>
          <div className={s.formHeading}>{t("leagues.createHeading")}</div>
          <div className={s.formRow}>
            <input
              className={s.input}
              value={name}
              onChange={e => { setName(e.target.value); setFormError(""); }}
              placeholder={t("leagues.namePlaceholder")}
              maxLength={80}
            />
            <button className={s.primaryBtn} disabled={creating}>{t("leagues.createBtn")}</button>
          </div>
        </form>

        <form className={s.formCard} onSubmit={submitJoin}>
          <div className={s.formHeading}>{t("leagues.joinHeading")}</div>
          <div className={s.formRow}>
            <input
              className={s.input}
              value={code}
              onChange={e => { setCode(e.target.value.toUpperCase()); setFormError(""); }}
              placeholder={t("leagues.codePlaceholder")}
              maxLength={10}
            />
            <button className={s.primaryBtn} disabled={joining}>{t("leagues.joinBtn")}</button>
          </div>
        </form>
      </div>

      {formError && <div className={s.formError}>{formError}</div>}

      {leagues.length === 0 ? (
        <div className={s.empty}>
          <p>{t("leagues.empty")}</p>
          <small>{t("leagues.emptyHint")}</small>
        </div>
      ) : (
        <div className={s.grid}>
          {leagues.map(l => (
            <button key={l.id} className={s.card} onClick={() => openLeague(l.id)}>
              <div className={s.cardName}>{l.name}</div>
              <div className={s.cardMeta}>
                {t("leagues.members", { count: l.member_count })}
                {l.is_owner && <span className={s.ownerTag}>{t("leagues.owner")}</span>}
              </div>
              <div className={s.cardCode}>{l.code}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
