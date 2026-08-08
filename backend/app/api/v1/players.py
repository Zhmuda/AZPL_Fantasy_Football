from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.league import Player, Season
from app.models.stats import PlayerMatchStat
from app.schemas.league import PlayerOut

router = APIRouter(prefix="/players", tags=["players"])


async def _players_with_stats(db: AsyncSession, where_clauses: list) -> list[dict]:
    active_season = await db.execute(select(Season).where(Season.is_active == True))
    season = active_season.scalar_one_or_none()
    season_id = season.id if season else None

    stats_sq = (
        select(
            PlayerMatchStat.player_id,
            func.coalesce(func.sum(PlayerMatchStat.goals), 0).label("season_goals"),
            func.coalesce(func.sum(PlayerMatchStat.assists), 0).label("season_assists"),
            func.coalesce(func.sum(PlayerMatchStat.fantasy_points), 0).label("season_points"),
            func.count(PlayerMatchStat.id).filter(PlayerMatchStat.minutes_played > 0).label("season_matches"),
        )
        .group_by(PlayerMatchStat.player_id)
        .subquery()
    )

    q = (
        select(
            Player,
            func.coalesce(stats_sq.c.season_goals, 0).label("season_goals"),
            func.coalesce(stats_sq.c.season_assists, 0).label("season_assists"),
            func.coalesce(stats_sq.c.season_points, 0).label("season_points"),
            func.coalesce(stats_sq.c.season_matches, 0).label("season_matches"),
        )
        .outerjoin(stats_sq, Player.id == stats_sq.c.player_id)
        .options(selectinload(Player.team))
        .where(Player.is_active == True, *where_clauses)
        .order_by(stats_sq.c.season_points.desc().nulls_last(), Player.name)
    )

    rows = await db.execute(q)
    result = []
    for row in rows.all():
        player = row[0]
        out = PlayerOut.model_validate(player)
        out.season_goals = row.season_goals
        out.season_assists = row.season_assists
        out.season_points = row.season_points
        out.season_matches = row.season_matches
        result.append(out)
    return result


@router.get("/", response_model=list[PlayerOut])
async def get_players(
    position: str | None = Query(None, pattern="^[GDMF]$"),
    team_id: int | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    where = []
    if position:
        where.append(Player.position == position)
    if team_id:
        where.append(Player.team_id == team_id)
    if search:
        where.append(Player.name.ilike(f"%{search}%"))
    return await _players_with_stats(db, where)


@router.get("/{player_id}", response_model=PlayerOut)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    result = await _players_with_stats(db, [Player.id == player_id])
    if not result:
        raise HTTPException(404, "Player not found")
    return result[0]
