import api from "./client";

export const getMyLeagues = (seasonId) =>
  api.get("/mini-leagues/my", { params: { season_id: seasonId } }).then(r => r.data);

export const createLeague = (name, seasonId) =>
  api.post("/mini-leagues", { name, season_id: seasonId }).then(r => r.data);

export const joinLeague = (code) =>
  api.post("/mini-leagues/join", { code }).then(r => r.data);

export const getLeagueStandings = (leagueId) =>
  api.get(`/mini-leagues/${leagueId}/standings`).then(r => r.data);

export const leaveLeague = (leagueId) =>
  api.post(`/mini-leagues/${leagueId}/leave`);
