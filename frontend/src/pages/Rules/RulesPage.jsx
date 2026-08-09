import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getSeasons } from "../../api/fantasy";
import s from "./RulesPage.module.css";

const SCORING_ROWS = [
  { key: "playedShort",     points: 1 },
  { key: "playedFull",      points: 2 },
  { key: "goalGkDef",       points: 6 },
  { key: "goalMid",         points: 5 },
  { key: "goalFwd",         points: 4 },
  { key: "assist",          points: 3 },
  { key: "cleanSheetGkDef", points: 4 },
  { key: "cleanSheetMid",   points: 1 },
  { key: "savesPerThree",   points: 1 },
  { key: "penaltySave",     points: 5 },
  { key: "penaltyMiss",     points: -2 },
  { key: "yellowCard",      points: -1 },
  { key: "redCard",         points: -3 },
  { key: "ownGoal",         points: -2 },
];

const PRICE_RANGES = [
  { pos: "G", min: 4.5, max: 6.0 },
  { pos: "D", min: 4.5, max: 7.5 },
  { pos: "M", min: 5.0, max: 10.0 },
  { pos: "F", min: 5.5, max: 12.0 },
];

export default function RulesPage() {
  const { t } = useTranslation();
  const [season, setSeason] = useState(null);

  useEffect(() => {
    getSeasons()
      .then(seasons => setSeason(seasons.find(x => x.is_active) ?? seasons[0] ?? null))
      .catch(() => {});
  }, []);

  const squadItems    = t("rules.squad.items", { returnObjects: true });
  const lineupItems   = t("rules.lineup.items", { returnObjects: true });
  const transferItems = t("rules.transfers.items", { returnObjects: true });
  const pricingItems  = t("rules.pricing.items", { returnObjects: true });

  return (
    <div className={s.page}>
      <div className={s.hero}>
        <h1 className={s.heading}>{t("rules.title")}</h1>
        <p className={s.sub}>{t("rules.subtitle", { season: season?.name ?? "" })}</p>
      </div>

      <section className={s.section}>
        <h2 className={s.sectionTitle}>👥 {t("rules.squad.heading")}</h2>
        <ul className={s.list}>
          {squadItems.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </section>

      <section className={s.section}>
        <h2 className={s.sectionTitle}>👑 {t("rules.lineup.heading")}</h2>
        <ul className={s.list}>
          {lineupItems.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </section>

      <section className={s.section}>
        <h2 className={s.sectionTitle}>🔄 {t("rules.transfers.heading")}</h2>
        <ul className={s.list}>
          {transferItems.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </section>

      <section className={s.section}>
        <h2 className={s.sectionTitle}>⚡ {t("rules.scoring.heading")}</h2>
        <p className={s.intro}>{t("rules.scoring.intro")}</p>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("rules.scoring.table.action")}</th>
                <th className={s.ptsHead}>{t("rules.scoring.table.points")}</th>
              </tr>
            </thead>
            <tbody>
              {SCORING_ROWS.map(row => (
                <tr key={row.key}>
                  <td>{t(`rules.scoring.rows.${row.key}`)}</td>
                  <td className={`${s.pts} ${row.points < 0 ? s.negative : ""}`}>
                    {row.points > 0 ? `+${row.points}` : row.points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={s.note}>{t("rules.scoring.captainNote")}</div>
        <div className={s.note}>{t("rules.scoring.benchNote")}</div>
      </section>

      <section className={s.section}>
        <h2 className={s.sectionTitle}>💰 {t("rules.pricing.heading")}</h2>
        <ul className={s.list}>
          {pricingItems.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
        <div className={s.rangesGrid}>
          {PRICE_RANGES.map(r => (
            <div key={r.pos} className={s.rangeCard}>
              <span className={`pos-badge pos-${r.pos}`}>{t(`players.positions.${r.pos}`)}</span>
              <div className={s.rangeVal}>£{r.min}m – £{r.max}m</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
