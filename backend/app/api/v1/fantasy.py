from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import User
from app.models.league import Player, Round
from app.models.fantasy import FantasyTeam, FantasyPick, FantasyRoundScore
from app.core.security import get_current_user
from app.schemas.fantasy import (
    FantasyTeamCreate, FantasyTeamOut, PickCreate,
    PickWithPlayerOut, LeaderboardEntry,
)

router = APIRouter(prefix="/fantasy", tags=["fantasy"])

MAX_TRANSFERS = 3


@router.post("/teams", response_model=FantasyTeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: FantasyTeamCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(FantasyTeam).where(
            FantasyTeam.user_id == user.id,
            FantasyTeam.season_id == body.season_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team already exists for this season")

    team = FantasyTeam(user_id=user.id, season_id=body.season_id, name=body.name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("/teams/my", response_model=FantasyTeamOut)
async def my_team(
    season_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FantasyTeam).where(
            FantasyTeam.user_id == user.id,
            FantasyTeam.season_id == season_id,
        )
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")

    # Rank: сколько команд набрало больше очков + 1
    rank_result = await db.execute(
        select(func.count(FantasyTeam.id) + 1).where(
            FantasyTeam.season_id == season_id,
            FantasyTeam.total_points > team.total_points,
        )
    )
    rank = rank_result.scalar_one()

    # Очки за последний завершённый тур
    last_result = await db.execute(
        select(FantasyRoundScore)
        .join(Round, FantasyRoundScore.round_id == Round.id)
        .where(FantasyRoundScore.fantasy_team_id == team.id)
        .order_by(Round.number.desc())
        .limit(1)
    )
    last_score = last_result.scalar_one_or_none()

    return FantasyTeamOut(
        id=team.id,
        name=team.name,
        budget=team.budget,
        total_points=team.total_points,
        rank=rank,
        last_round_points=last_score.points if last_score else None,
    )


@router.get("/teams/my/picks", response_model=list[PickWithPlayerOut])
async def my_picks(
    season_id: int,
    round_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_result = await db.execute(
        select(FantasyTeam).where(
            FantasyTeam.user_id == user.id,
            FantasyTeam.season_id == season_id,
        )
    )
    team = team_result.scalar_one_or_none()
    if not team:
        return []

    result = await db.execute(
        select(FantasyPick)
        .options(
            selectinload(FantasyPick.player).selectinload(Player.team)
        )
        .where(FantasyPick.fantasy_team_id == team.id, FantasyPick.round_id == round_id)
        .order_by(FantasyPick.slot)
    )
    return result.scalars().all()


@router.put("/teams/my/picks", response_model=list[PickWithPlayerOut])
async def replace_my_picks(
    season_id: int,
    body: list[PickCreate],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_result = await db.execute(
        select(FantasyTeam).where(
            FantasyTeam.user_id == user.id,
            FantasyTeam.season_id == season_id,
        )
    )
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Команда не найдена")

    if len(body) != 15:
        raise HTTPException(400, "Состав должен содержать ровно 15 игроков")

    round_ids = {p.round_id for p in body}
    if len(round_ids) != 1:
        raise HTTPException(400, "Все игроки должны относиться к одному туру")
    round_id = round_ids.pop()

    round_obj = await db.get(Round, round_id)
    if not round_obj:
        raise HTTPException(400, "Тур не найден")
    # deadline is stored naive/UTC (timestamp without time zone) — compare naive-to-naive
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if round_obj.deadline and now >= round_obj.deadline:
        raise HTTPException(400, "Дедлайн тура истёк — редактирование состава закрыто")

    if sorted(p.slot for p in body) != list(range(1, 16)):
        raise HTTPException(400, "Слоты должны быть от 1 до 15 без повторов")

    player_ids = [p.player_id for p in body]
    if len(set(player_ids)) != 15:
        raise HTTPException(400, "В составе не может быть повторяющихся игроков")

    captains = [p for p in body if p.is_captain]
    vcs = [p for p in body if p.is_vice_captain]
    if len(captains) != 1 or len(vcs) != 1:
        raise HTTPException(400, "Нужно выбрать одного капитана и одного вице-капитана")
    if captains[0].player_id == vcs[0].player_id:
        raise HTTPException(400, "Капитан и вице-капитан должны быть разными игроками")

    players_result = await db.execute(select(Player).where(Player.id.in_(player_ids)))
    players = {p.id: p for p in players_result.scalars().all()}
    if len(players) != 15:
        raise HTTPException(400, "В составе указан неизвестный игрок")

    pos_counts = {"G": 0, "D": 0, "M": 0, "F": 0}
    club_counts: dict[int, int] = {}
    total_price = 0.0
    for pid in player_ids:
        pl = players[pid]
        pos_counts[pl.position] += 1
        total_price += pl.price
        if pl.team_id:
            club_counts[pl.team_id] = club_counts.get(pl.team_id, 0) + 1

    if pos_counts != {"G": 2, "D": 5, "M": 5, "F": 3}:
        raise HTTPException(400, "Состав должен быть 2 ВРТ, 5 ЗАЩ, 5 ПЗН, 3 НАП")
    if total_price > 100:
        raise HTTPException(400, "Превышен бюджет £100m")
    if any(c > 3 for c in club_counts.values()):
        raise HTTPException(400, "Максимум 3 игрока из одного клуба")

    starter_pos_counts = {"G": 0, "D": 0, "M": 0, "F": 0}
    for p in body:
        if p.slot <= 11:
            starter_pos_counts[players[p.player_id].position] += 1
    if starter_pos_counts["G"] != 1 or sum(starter_pos_counts.values()) != 11:
        raise HTTPException(400, "Некорректный стартовый состав")

    existing_result = await db.execute(
        select(FantasyPick.player_id).where(
            FantasyPick.fantasy_team_id == team.id,
            FantasyPick.round_id == round_id,
        )
    )
    existing_ids = {row[0] for row in existing_result.all()}
    # Only cap changes once a squad already exists for this round — the very
    # first save (building the squad from scratch) isn't a "transfer".
    if existing_ids:
        transfers = len(set(player_ids) - existing_ids)
        if transfers > MAX_TRANSFERS:
            raise HTTPException(400, f"Максимум {MAX_TRANSFERS} трансферов за раз")

    await db.execute(
        delete(FantasyPick).where(
            FantasyPick.fantasy_team_id == team.id,
            FantasyPick.round_id == round_id,
        )
    )
    for p in body:
        db.add(FantasyPick(fantasy_team_id=team.id, **p.model_dump()))
    await db.commit()

    result = await db.execute(
        select(FantasyPick)
        .options(selectinload(FantasyPick.player).selectinload(Player.team))
        .where(FantasyPick.fantasy_team_id == team.id, FantasyPick.round_id == round_id)
        .order_by(FantasyPick.slot)
    )
    return result.scalars().all()


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(season_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FantasyTeam, User)
        .join(User, FantasyTeam.user_id == User.id)
        .where(FantasyTeam.season_id == season_id)
        .order_by(FantasyTeam.total_points.desc())
        .limit(100)
    )
    rows = result.all()
    return [
        LeaderboardEntry(
            rank=i + 1,
            team_name=team.name,
            username=user.username,
            total_points=team.total_points,
        )
        for i, (team, user) in enumerate(rows)
    ]
