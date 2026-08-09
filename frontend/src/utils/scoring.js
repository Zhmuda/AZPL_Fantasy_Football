// Mirrors collector/tasks/calc_points.py's SCORING table and _calc() — kept
// in sync manually since the frontend has no access to the Python module.
export function breakdownPoints(stat, position) {
  const lines = [];

  if (stat.minutes_played >= 60) {
    lines.push({ key: "playedFull", count: 1, unit: 2 });
  } else if (stat.minutes_played > 0) {
    lines.push({ key: "playedShort", count: 1, unit: 1 });
  }

  if (stat.goals > 0) {
    const goalKey  = position === "F" ? "goalFwd" : position === "M" ? "goalMid" : "goalGkDef";
    const goalUnit = position === "F" ? 4 : position === "M" ? 5 : 6;
    lines.push({ key: goalKey, count: stat.goals, unit: goalUnit });
  }

  if (stat.assists > 0) {
    lines.push({ key: "assist", count: stat.assists, unit: 3 });
  }

  const saveUnits = Math.floor((stat.saves || 0) / 3);
  if (saveUnits > 0) {
    lines.push({ key: "savesPerThree", count: saveUnits, unit: 1 });
  }

  if (stat.penalty_save > 0) lines.push({ key: "penaltySave", count: stat.penalty_save, unit: 5 });
  if (stat.penalty_miss > 0) lines.push({ key: "penaltyMiss", count: stat.penalty_miss, unit: -2 });
  if (stat.yellow_cards > 0) lines.push({ key: "yellowCard", count: stat.yellow_cards, unit: -1 });
  if (stat.red_cards   > 0) lines.push({ key: "redCard",    count: stat.red_cards,   unit: -3 });
  if (stat.own_goals   > 0) lines.push({ key: "ownGoal",    count: stat.own_goals,   unit: -2 });

  if (stat.clean_sheet && stat.minutes_played >= 60 && position !== "F") {
    const csKey  = position === "M" ? "cleanSheetMid" : "cleanSheetGkDef";
    const csUnit = position === "M" ? 1 : 4;
    lines.push({ key: csKey, count: 1, unit: csUnit });
  }

  return lines.map(l => ({ ...l, total: l.count * l.unit }));
}
