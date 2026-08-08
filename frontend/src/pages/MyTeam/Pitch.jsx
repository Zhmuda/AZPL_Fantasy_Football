import { useState } from "react";
import { useTranslation } from "react-i18next";
import s from "./Pitch.module.css";

const ROW_Y = { F: 12, M: 35, D: 60, G: 84 };

const xPositions = (n) => {
  if (n === 1) return [50];
  if (n === 2) return [30, 70];
  if (n === 3) return [20, 50, 80];
  if (n === 4) return [14, 38, 62, 86];
  if (n === 5) return [10, 27.5, 50, 72.5, 90];
  return [];
};

function PlayerToken({ pick, x, y, open, onOpen, onClose, isCaptain, isVC, onCaptain, onVC, onRemove }) {
  const { t } = useTranslation();
  const lastName = pick.player.name.split(" ").slice(-1)[0];
  const pos = pick.player.position;
  const inactive = pick.player.is_active === false;

  return (
    <div className={s.token} style={{ left: `${x}%`, top: `${y}%` }}>
      <div
        className={`${s.circle} ${s[`pos${pos}`]} ${inactive ? s.circleInactive : ""}`}
        onClick={e => { e.stopPropagation(); open ? onClose() : onOpen(); }}
        title={inactive ? t("myTeam.bench.inactiveTitle") : undefined}
      >
        {pos}
        {isCaptain && <span className={s.capBadge}>C</span>}
        {isVC && !isCaptain && <span className={s.vcBadge}>V</span>}
        {inactive && <span className={s.warnBadge}>!</span>}
      </div>
      <div className={s.name}>{lastName}</div>
      <div className={s.pts}>{pick.player.season_points}{t("myTeam.playerCard.points")}</div>

      {open && (
        <div className={s.menu} onClick={e => e.stopPropagation()}>
          <button onClick={onCaptain}>👑 {t("myTeam.bench.captainTitle")}</button>
          <button onClick={onVC}>⭐ {t("myTeam.bench.vcTitle")}</button>
          <button className={s.rmBtn} onClick={onRemove}>✕ {t("myTeam.bench.removeAction")}</button>
        </div>
      )}
    </div>
  );
}

export default function Pitch({ starters, captainId, viceCaptainId, onCaptain, onVC, onRemove }) {
  const [openId, setOpenId] = useState(null);

  return (
    <div className={s.pitch} onClick={() => setOpenId(null)}>
      <div className={s.centerLine} />
      <div className={s.centerCircle} />
      <div className={s.penaltyTop} />
      <div className={s.penaltyBot} />

      {["G", "D", "M", "F"].map(pos => {
        const group = starters[pos] || [];
        const xs = xPositions(group.length);
        const y = ROW_Y[pos];
        return group.map((pick, i) => (
          <PlayerToken
            key={pick.player.id}
            pick={pick}
            x={xs[i]}
            y={y}
            open={openId === pick.player.id}
            onOpen={() => setOpenId(pick.player.id)}
            onClose={() => setOpenId(null)}
            isCaptain={captainId === pick.player.id}
            isVC={viceCaptainId === pick.player.id}
            onCaptain={() => { onCaptain(pick.player.id); setOpenId(null); }}
            onVC={() => { onVC(pick.player.id); setOpenId(null); }}
            onRemove={() => { onRemove(pick.player.id); setOpenId(null); }}
          />
        ));
      })}
    </div>
  );
}
