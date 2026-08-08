import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../context/AuthContext";
import {
  getSeasons, getRounds, getMyTeam, createTeam,
  getTeams, getMyPicks, updateMyPicks,
} from "../../api/fantasy";
import { getPlayers } from "../../api/players";
import Pitch from "./Pitch";
import s from "./MyTeamPage.module.css";

const FORMATIONS = {
  "4-4-2": { G: 1, D: 4, M: 4, F: 2 },
  "4-3-3": { G: 1, D: 4, M: 3, F: 3 },
  "5-2-3": { G: 1, D: 5, M: 2, F: 3 },
};
const POS_LIMITS = { G: 2, D: 5, M: 5, F: 3 };
const CLUB_LIMIT = 3;
const BUDGET     = 100;
const MAX_TRANSFERS = 3;

const PRICE_MAX_OPTIONS = [99, 5, 7, 9, 12];
const SORT_OPTIONS = [
  { value: "season_points",  labelKey: "common.sortPoints" },
  { value: "season_goals",   labelKey: "common.sortGoals" },
  { value: "season_assists", labelKey: "common.sortAssists" },
  { value: "price",          labelKey: "common.sortPrice" },
];

// ─── Bench card ──────────────────────────────────────────────────────────────
function BenchCard({ pick, isCaptain, isVC, onCaptain, onVC, onRemove }) {
  const { t } = useTranslation();
  const pos = pick.player.position;
  const inactive = pick.player.is_active === false;
  return (
    <div className={s.benchCard}>
      <div
        className={`${s.benchCircle} ${s[`pos${pos}`]} ${inactive ? s.benchCircleInactive : ""}`}
        title={inactive ? t("myTeam.bench.inactiveTitle") : undefined}
      >{pos}</div>
      <div className={s.benchInfo}>
        <div className={s.benchName}>
          {pick.player.name.split(" ").slice(-1)[0]}
          {inactive && <span className={s.inactiveTag} title={t("myTeam.bench.inactiveTitle")}>{t("myTeam.bench.inactiveTag")}</span>}
        </div>
        <div className={s.benchSub}>{pick.player.team?.name ?? t("common.dash")} · £{pick.player.price}m</div>
      </div>
      {onRemove && (
        <div className={s.benchActions}>
          <button className={isCaptain ? s.badgeOn : s.badge} onClick={onCaptain} title={t("myTeam.bench.captainTitle")}>C</button>
          <button className={isVC     ? s.badgeOn : s.badge} onClick={onVC}      title={t("myTeam.bench.vcTitle")}>VC</button>
          <button className={s.rmSmall} onClick={onRemove}>✕</button>
        </div>
      )}
    </div>
  );
}

// ─── Stat card (очки / место / тур) ─────────────────────────────────────────
function StatCard({ label, value, sub, accent }) {
  return (
    <div className={s.statCard}>
      <div className={`${s.statVal} ${accent ? s.statAccent : ""}`}>{value ?? "—"}</div>
      <div className={s.statLabel}>{label}</div>
      {sub && <div className={s.statSub}>{sub}</div>}
    </div>
  );
}

// ─── Шаг 1: создание команды ─────────────────────────────────────────────────
function NameStep({ name, setName, formation, setFormation, onNext }) {
  const { t } = useTranslation();
  return (
    <div className={s.nameStep}>
      <div className={s.nameCard}>
        <div className={s.nameEmoji}>⚽</div>
        <h2 className={s.nameHeading}>{t("myTeam.nameStep.heading")}</h2>
        <p className={s.nameSub}>{t("myTeam.nameStep.subtitle")}</p>

        <div className={s.nameField}>
          <label className={s.nameLabel}>{t("myTeam.nameStep.teamNameLabel")}</label>
          <input
            className={s.nameInput}
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder={t("myTeam.nameStep.teamNamePlaceholder")}
            maxLength={50}
            autoFocus
          />
        </div>

        <div className={s.nameField}>
          <label className={s.nameLabel}>{t("myTeam.nameStep.formationLabel")}</label>
          <div className={s.fmtnRow}>
            {Object.keys(FORMATIONS).map(f => (
              <button
                key={f}
                className={formation === f ? s.fmtnActive : s.fmtnBtn}
                onClick={() => setFormation(f)}
              >{f}</button>
            ))}
          </div>
        </div>

        <div className={s.nameRules}>
          <div className={s.ruleItem}><span>👥</span> {t("myTeam.nameStep.rules.clubLimit")}</div>
          <div className={s.ruleItem}><span>👑</span> {t("myTeam.nameStep.rules.captainDouble")}</div>
          <div className={s.ruleItem}><span>⭐</span> {t("myTeam.nameStep.rules.vcDouble")}</div>
          <div className={s.ruleItem}><span>💰</span> {t("myTeam.nameStep.rules.budget")}</div>
        </div>

        <button
          className={s.nameNextBtn}
          disabled={!name.trim()}
          onClick={onNext}
        >
          {t("myTeam.nameStep.nextBtn")}
        </button>
      </div>
    </div>
  );
}

// ─── Шаг 3: просмотр сохранённой команды ────────────────────────────────────
function ViewStep({ myTeam, savedPicks, allPlayers, season, round, onEdit }) {
  const { t } = useTranslation();
  const starters  = { G: [], D: [], M: [], F: [] };
  const bench     = [];

  const enriched = savedPicks.map(pick => {
    const full = allPlayers.find(p => p.id === pick.player.id);
    return {
      ...pick,
      player: { ...pick.player, season_points: full?.season_points ?? 0 },
    };
  });

  for (const pick of enriched) {
    if (pick.slot <= 11) {
      const pos = pick.player.position;
      if (starters[pos]) starters[pos].push(pick);
    } else {
      bench.push(pick);
    }
  }

  const captainId     = enriched.find(p => p.is_captain)?.player.id     ?? null;
  const viceCaptainId = enriched.find(p => p.is_vice_captain)?.player.id ?? null;

  // Определяем схему по количеству стартовых игроков
  const dCount = starters.D.length;
  const mCount = starters.M.length;
  const fCount = starters.F.length;
  const formationLabel = `${dCount}-${mCount}-${fCount}`;

  return (
    <div className={s.viewStep}>
      <div className={s.editBar}>
        <button className={s.editBtn} onClick={onEdit}>{t("myTeam.editBtn")}</button>
      </div>

      {/* Статистика команды */}
      <div className={s.statsRow}>
        <StatCard
          label={t("myTeam.stats.totalPoints")}
          value={myTeam.total_points}
          sub={t("myTeam.stats.season", { name: season?.name ?? "" })}
          accent
        />
        <StatCard
          label={t("myTeam.stats.rank")}
          value={myTeam.rank ? `#${myTeam.rank}` : t("common.dash")}
          sub={t("myTeam.stats.amongTeams")}
        />
        <StatCard
          label={t("myTeam.stats.lastRound")}
          value={myTeam.last_round_points ?? t("common.dash")}
          sub={round ? t("myTeam.round", { number: round.number }) : ""}
        />
        <StatCard
          label={t("myTeam.stats.formation")}
          value={formationLabel}
          sub={t("myTeam.stats.playersCount", { count: enriched.length })}
        />
      </div>

      {/* Поле */}
      <Pitch
        starters={starters}
        captainId={captainId}
        viceCaptainId={viceCaptainId}
        onCaptain={() => {}}
        onVC={() => {}}
        onRemove={() => {}}
      />

      {/* Скамейка */}
      {bench.length > 0 && (
        <div className={s.benchSection}>
          <div className={s.benchHeader}>
            <span className={s.benchTitle}>{t("myTeam.bench.title")}</span>
            <span className={s.benchSub2}>{t("myTeam.bench.count", { count: bench.length })}</span>
          </div>
          <div className={s.benchList}>
            {bench.map(pick => (
              <BenchCard key={pick.id} pick={pick}
                isCaptain={captainId === pick.player.id}
                isVC={viceCaptainId === pick.player.id}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Главный компонент ───────────────────────────────────────────────────────
export default function MyTeamPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate  = useNavigate();

  const [season, setSeason]         = useState(null);
  const [round, setRound]           = useState(null);
  const [myTeam, setMyTeam]         = useState(null);
  const [savedPicks, setSavedPicks] = useState([]);
  const [allPlayers, setAllPlayers] = useState([]);
  const [teams, setTeams]           = useState([]);

  // Шаги: loading → name → build → view → edit
  const [step, setStep]             = useState("loading");
  const [teamName, setTeamName]     = useState("");
  const [formation, setFormation]   = useState("4-4-2");
  const [picks, setPicks]           = useState([]);
  const [saving, setSaving]         = useState(false);
  const [msg, setMsg]               = useState("");
  const [originalIds, setOriginalIds] = useState(() => new Set());

  // Фильтры пикера
  const [pickerPos, setPickerPos]       = useState("G");
  const [pickerTeam, setPickerTeam]     = useState("");
  const [pickerMax, setPickerMax]       = useState(99);
  const [pickerSort, setPickerSort]     = useState("season_points");
  const [pickerSearch, setPickerSearch] = useState("");

  useEffect(() => {
    if (!user) { navigate("/auth"); return; }

    const init = async () => {
      const [seasons, players, teamList] = await Promise.all([
        getSeasons(), getPlayers(), getTeams(),
      ]);
      setAllPlayers(players);
      setTeams(teamList);

      const active    = seasons.find(s => s.is_active) ?? seasons[0];
      setSeason(active);
      const rs = await getRounds(active.id);
      // Тур для сборки/просмотра состава — ближайший ещё не завершённый,
      // а не последний элемент списка (это финал сезона, а не текущий тур).
      const currentRound = rs.find(r => r.status !== "finished") ?? rs[rs.length - 1];
      setRound(currentRound);

      try {
        const teamData = await getMyTeam(active.id);
        setMyTeam(teamData);
        setTeamName(teamData.name);

        const p = await getMyPicks(active.id, currentRound.id);
        setSavedPicks(p);

        // Есть picks → view; есть команда без picks → build
        setStep(p.length > 0 ? "view" : "build");
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error("Failed to load team:", err);
        }
        // Команды нет (404) → первый заход. Другие ошибки тоже приземляются
        // сюда, чтобы не блокировать пользователя — но хотя бы залогированы.
        setStep("name");
      }
    };

    init();
  }, [user, navigate]);

  // ── Производные: стартовые и скамейка ────────────────────────────────────
  const { starters, bench } = useMemo(() => {
    const fmt = FORMATIONS[formation];
    const starters = { G: [], D: [], M: [], F: [] };
    const bench    = [];
    for (const pos of ["G", "D", "M", "F"]) {
      const group    = picks.filter(p => p.player.position === pos);
      starters[pos]  = group.slice(0, fmt[pos]);
      bench.push(...group.slice(fmt[pos]));
    }
    return { starters, bench };
  }, [picks, formation]);

  const captainId     = picks.find(p => p.is_captain)?.player.id     ?? null;
  const viceCaptainId = picks.find(p => p.is_vice_captain)?.player.id ?? null;
  const budgetUsed    = picks.reduce((sum, p) => sum + (p.player.price || 0), 0);
  const budgetLeft    = BUDGET - budgetUsed;

  // Трансферы: сколько игроков в текущем составе отсутствовали в исходном (только в режиме edit)
  const transfersUsed = step === "edit"
    ? picks.filter(p => !originalIds.has(p.player.id)).length
    : 0;

  // ── Валидация добавления ──────────────────────────────────────────────────
  const canAdd = useCallback((player) => {
    if (picks.find(p => p.player.id === player.id)) return false;
    if (picks.filter(p => p.player.position === player.position).length >= POS_LIMITS[player.position]) return false;
    if (budgetLeft < player.price) return false;
    if (picks.length >= 15) return false;
    const clubId = player.team?.id;
    if (clubId && picks.filter(p => p.player.team?.id === clubId).length >= CLUB_LIMIT) return false;
    if (step === "edit" && !originalIds.has(player.id) && transfersUsed >= MAX_TRANSFERS) return false;
    return true;
  }, [picks, budgetLeft, step, originalIds, transfersUsed]);

  const blockReason = (player) => {
    if (picks.find(p => p.player.id === player.id)) return t("myTeam.blockReasons.alreadyAdded");
    if (picks.filter(p => p.player.position === player.position).length >= POS_LIMITS[player.position]) return t("myTeam.blockReasons.positionLimit");
    if (budgetLeft < player.price) return t("myTeam.blockReasons.notEnoughBudget");
    if (picks.length >= 15) return t("myTeam.blockReasons.squadFull");
    const clubId = player.team?.id;
    if (clubId && picks.filter(p => p.player.team?.id === clubId).length >= CLUB_LIMIT) return t("myTeam.blockReasons.clubLimit");
    if (step === "edit" && !originalIds.has(player.id) && transfersUsed >= MAX_TRANSFERS) return t("myTeam.blockReasons.transferLimit");
    return "";
  };

  const addPlayer = (player) => {
    if (!canAdd(player)) return;
    setPicks(prev => [...prev, { player, is_captain: false, is_vice_captain: false }]);
  };

  const removePlayer = (playerId) =>
    setPicks(prev => prev.filter(p => p.player.id !== playerId));

  const setCaptain = (playerId) =>
    setPicks(prev => prev.map(p => ({
      ...p,
      is_captain: p.player.id === playerId,
      is_vice_captain: p.is_vice_captain && p.player.id !== playerId,
    })));

  const setViceCaptain = (playerId) =>
    setPicks(prev => prev.map(p => ({
      ...p,
      is_vice_captain: p.player.id === playerId && !p.is_captain,
    })));

  // ── Сохранение (слоты 1-11 = старт, 12-15 = скамейка) ───────────────────
  const save = async () => {
    if (!round) return;
    setSaving(true); setMsg("");
    try {
      let team = myTeam;
      if (!team) {
        team = await createTeam(teamName, season.id);
        setMyTeam(team);
      }

      const ordered = [
        ...starters.G, ...starters.D, ...starters.M, ...starters.F,
        ...bench,
      ];

      const body = ordered.map((pick, i) => ({
        player_id:       pick.player.id,
        round_id:        round.id,
        slot:            i + 1,
        is_captain:      pick.is_captain,
        is_vice_captain: pick.is_vice_captain,
      }));

      const savedP = await updateMyPicks(season.id, body);

      // Перезагружаем команду (теперь rank / last_round_points заполнены)
      const refreshedTeam = await getMyTeam(season.id);
      setMyTeam(refreshedTeam);
      setSavedPicks(savedP);
      setPicks([]);
      setStep("view");
    } catch (e) {
      setMsg("❌ " + (e.response?.data?.detail ?? t("myTeam.save.genericError")));
    } finally {
      setSaving(false);
    }
  };

  // ── Вход/выход из режима редактирования ──────────────────────────────────
  const enterEdit = () => {
    const editPicks = savedPicks.map(pick => {
      const full = allPlayers.find(p => p.id === pick.player.id);
      return {
        player: { ...pick.player, season_points: full?.season_points ?? 0 },
        is_captain: pick.is_captain,
        is_vice_captain: pick.is_vice_captain,
      };
    });

    // Определяем схему по стартовому составу (slot <= 11)
    const counts = { D: 0, M: 0, F: 0 };
    savedPicks.filter(p => p.slot <= 11).forEach(p => {
      if (counts[p.player.position] !== undefined) counts[p.player.position]++;
    });
    const matched = Object.entries(FORMATIONS).find(
      ([, f]) => f.D === counts.D && f.M === counts.M && f.F === counts.F
    );
    setFormation(matched ? matched[0] : "4-4-2");

    setOriginalIds(new Set(editPicks.map(p => p.player.id)));
    setPicks(editPicks);
    setMsg("");
    setStep("edit");
  };

  const cancelEdit = () => {
    setPicks([]);
    setMsg("");
    setStep("view");
  };

  // ── Пикер: фильтрация ─────────────────────────────────────────────────────
  const filtered = useMemo(() => allPlayers
    .filter(p => p.position === pickerPos)
    .filter(p => !pickerTeam || String(p.team?.id) === pickerTeam)
    .filter(p => p.price <= pickerMax)
    .filter(p => !pickerSearch || p.name.toLowerCase().includes(pickerSearch.toLowerCase()))
    .sort((a, b) => b[pickerSort] - a[pickerSort]),
    [allPlayers, pickerPos, pickerTeam, pickerMax, pickerSort, pickerSearch]
  );

  const countByPos = (pos) => picks.filter(p => p.player.position === pos).length;

  // ── Рендер ────────────────────────────────────────────────────────────────
  if (step === "loading") {
    return <div className={s.centered}><div className={s.spinner} /></div>;
  }

  if (step === "name") {
    return (
      <NameStep
        name={teamName} setName={setTeamName}
        formation={formation} setFormation={setFormation}
        onNext={() => setStep("build")}
      />
    );
  }

  if (step === "view") {
    return (
      <div className={s.page}>
        <div className={s.header}>
          <div>
            <h1>{myTeam?.name}</h1>
            <p className={s.sub}>{season?.name} · {round ? t("myTeam.round", { number: round.number }) : ""}</p>
          </div>
        </div>
        <ViewStep
          myTeam={myTeam}
          savedPicks={savedPicks}
          allPlayers={allPlayers}
          season={season}
          round={round}
          onEdit={enterEdit}
        />
      </div>
    );
  }

  // step === "build" | "edit"
  const isEditing = step === "edit";
  return (
    <div className={s.page}>
      <div className={s.header}>
        <div>
          <h1>{isEditing ? myTeam?.name : (teamName || t("myTeam.defaultTeamName"))}</h1>
          <p className={s.sub}>
            {season?.name} · {round ? t("myTeam.round", { number: round.number }) : ""}
            {isEditing && t("myTeam.editingSuffix")}
          </p>
        </div>
        <div className={s.headerRight}>
          {isEditing && (
            <div className={s.countBox}>
              <span className={s.budgetLabel}>{t("myTeam.budgetBox.transfers")}</span>
              <span className={transfersUsed > MAX_TRANSFERS ? s.budgetOver : s.budgetOk}>
                {transfersUsed}/{MAX_TRANSFERS}
              </span>
            </div>
          )}
          <div className={s.budgetBox}>
            <span className={s.budgetLabel}>{t("myTeam.budgetBox.budget")}</span>
            <span className={budgetLeft < 0 ? s.budgetOver : s.budgetOk}>
              £{budgetLeft.toFixed(1)}m
            </span>
          </div>
          <div className={s.countBox}>
            <span className={s.budgetLabel}>{t("myTeam.budgetBox.players")}</span>
            <span className={s.budgetOk}>{picks.length}/15</span>
          </div>
        </div>
      </div>

      <div className={s.formationBar}>
        <span className={s.formationLabel}>{t("myTeam.formationLabel")}</span>
        {Object.keys(FORMATIONS).map(f => (
          <button key={f}
            className={formation === f ? s.fmtnActive : s.fmtnBtn}
            onClick={() => setFormation(f)}
          >{f}</button>
        ))}
      </div>

      <div className={s.layout}>
        {/* Лево: поле + скамейка + сохранение */}
        <div className={s.pitchSide}>
          <Pitch
            starters={starters}
            captainId={captainId}
            viceCaptainId={viceCaptainId}
            onCaptain={setCaptain}
            onVC={setViceCaptain}
            onRemove={removePlayer}
          />

          <div className={s.benchSection}>
            <div className={s.benchHeader}>
              <span className={s.benchTitle}>{t("myTeam.bench.title")}</span>
              <span className={s.benchSub2}>{t("myTeam.bench.count", { count: bench.length })}</span>
            </div>
            {bench.length === 0
              ? <div className={s.benchEmpty}>{t("myTeam.bench.autoFormed")}</div>
              : <div className={s.benchList}>
                  {bench.map(pick => (
                    <BenchCard key={pick.player.id} pick={pick}
                      isCaptain={captainId === pick.player.id}
                      isVC={viceCaptainId === pick.player.id}
                      onCaptain={() => setCaptain(pick.player.id)}
                      onVC={() => setViceCaptain(pick.player.id)}
                      onRemove={() => removePlayer(pick.player.id)}
                    />
                  ))}
                </div>
            }
          </div>

          <div className={s.saveArea}>
            {msg && <div className={s.msg}>{msg}</div>}
            <button
              className={s.saveBtn}
              disabled={picks.length < 15 || saving || budgetLeft < 0 || transfersUsed > MAX_TRANSFERS}
              onClick={save}
            >
              {saving ? t("myTeam.save.saving") : isEditing ? t("myTeam.save.saveChanges") : t("myTeam.save.saveTeam")}
            </button>
            {isEditing && (
              <button className={s.cancelBtn} disabled={saving} onClick={cancelEdit}>
                {t("myTeam.save.cancel")}
              </button>
            )}
            {picks.length < 15 && (
              <p className={s.hint}>{t("myTeam.save.needMore", { count: 15 - picks.length })}</p>
            )}
            {isEditing && transfersUsed > MAX_TRANSFERS && (
              <p className={s.hint}>{t("myTeam.save.transferLimitExceeded", { max: MAX_TRANSFERS })}</p>
            )}
          </div>
        </div>

        {/* Право: пикер */}
        <div className={s.pickerSide}>
          <div className={s.pickerHead}>
            <div className={s.pickerTitle}>{t("myTeam.picker.addPlayer")}</div>

            <div className={s.posTabs}>
              {Object.keys(POS_LIMITS).map(pos => (
                <button key={pos}
                  className={pickerPos === pos ? s.posActive : s.posBtn}
                  onClick={() => setPickerPos(pos)}
                >
                  <span className={`pos-badge pos-${pos}`}>{pos}</span>
                  <span className={s.posCount}>{countByPos(pos)}/{POS_LIMITS[pos]}</span>
                </button>
              ))}
            </div>

            <div className={s.filterRow}>
              <select className={s.sel} value={pickerTeam} onChange={e => setPickerTeam(e.target.value)}>
                <option value="">{t("common.allClubs")}</option>
                {teams.map(tm => <option key={tm.id} value={tm.id}>{tm.name}</option>)}
              </select>
              <select className={s.sel} value={pickerMax} onChange={e => setPickerMax(Number(e.target.value))}>
                {PRICE_MAX_OPTIONS.map(v => (
                  <option key={v} value={v}>{v === 99 ? t("common.anyPrice") : t("common.upTo", { price: v })}</option>
                ))}
              </select>
              <select className={s.sel} value={pickerSort} onChange={e => setPickerSort(e.target.value)}>
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{t(o.labelKey)}</option>)}
              </select>
            </div>

            <input className={s.search} placeholder={t("common.searchByName")}
              value={pickerSearch} onChange={e => setPickerSearch(e.target.value)} />
          </div>

          <div className={s.playerList}>
            {filtered.length === 0 && <div className={s.empty}>{t("players.empty")}</div>}
            {filtered.map(p => {
              const added = !!picks.find(pk => pk.player.id === p.id);
              const ok    = canAdd(p);
              const why   = !added && !ok ? blockReason(p) : "";
              return (
                <div key={p.id}
                  className={`${s.playerRow} ${added ? s.playerAdded : ""}`}
                  title={why}
                >
                  <div className={s.pInfo}>
                    {p.photo_url && (
                      <img src={p.photo_url} alt="" className={s.pAvatar}
                        onError={e => { e.target.style.display = "none"; }} />
                    )}
                    <div>
                      <div className={s.pName}>{p.name}</div>
                      <div className={s.pTeam}>{p.team?.name ?? t("common.dash")}</div>
                    </div>
                  </div>
                  <div className={s.pRight}>
                    <div className={s.pPts}>
                      {p.season_points}<span className={s.pPtsLabel}>{t("myTeam.playerCard.points")}</span>
                    </div>
                    <div className={s.pPrice}>£{p.price}m</div>
                    <button
                      className={added ? s.addedBtn : ok ? s.addBtn : s.disabledBtn}
                      onClick={() => !added && addPlayer(p)}
                      disabled={added || !ok}
                    >
                      {added ? "✓" : "+"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
