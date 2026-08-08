import api from "./client";

export const getSeasons = () =>
  api.get("/matches/seasons").then(r => r.data);

export const getTeams = () =>
  api.get("/matches/teams").then(r => r.data);

export const getRounds = (seasonId) =>
  api.get(`/matches/seasons/${seasonId}/rounds`).then(r => r.data);

export const getLeaderboard = (seasonId) =>
  api.get("/fantasy/leaderboard", { params: { season_id: seasonId } }).then(r => r.data);

export const getMyTeam = (seasonId) =>
  api.get("/fantasy/teams/my", { params: { season_id: seasonId } }).then(r => r.data);

export const createTeam = (name, season_id) =>
  api.post("/fantasy/teams", { name, season_id }).then(r => r.data);

export const getMyPicks = (seasonId, roundId) =>
  api.get("/fantasy/teams/my/picks", { params: { season_id: seasonId, round_id: roundId } }).then(r => r.data);

export const updateMyPicks = (seasonId, picks) =>
  api.put("/fantasy/teams/my/picks", picks, { params: { season_id: seasonId } }).then(r => r.data);
