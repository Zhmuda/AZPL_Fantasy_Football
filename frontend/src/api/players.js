import api from "./client";

export const getPlayers = (params = {}) =>
  api.get("/players/", { params }).then(r => r.data);

export const getPlayer = (id) =>
  api.get(`/players/${id}`).then(r => r.data);
