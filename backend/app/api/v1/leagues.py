import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.fantasy import FantasyTeam
from app.models.private_league import MiniLeague, MiniLeagueMember
from app.core.security import get_current_user
from app.schemas.mini_league import (
    MiniLeagueCreate, MiniLeagueJoin, MiniLeagueOut,
    MiniLeagueStandingsOut, MiniLeagueStandingEntry,
)

router = APIRouter(prefix="/mini-leagues", tags=["mini-leagues"])

# Excludes visually ambiguous characters (0/O, 1/I/L) so codes are easy to
# read aloud or retype from a friend's screen.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


async def _generate_code(db: AsyncSession) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        existing = await db.execute(select(MiniLeague.id).where(MiniLeague.code == code))
        if existing.scalar_one_or_none() is None:
            return code
    raise HTTPException(500, "Не удалось сгенерировать код лиги, попробуйте ещё раз")


async def _to_out(league: MiniLeague, db: AsyncSession, user_id: int) -> MiniLeagueOut:
    count_result = await db.execute(
        select(func.count(MiniLeagueMember.id)).where(MiniLeagueMember.league_id == league.id)
    )
    return MiniLeagueOut(
        id=league.id,
        name=league.name,
        code=league.code,
        season_id=league.season_id,
        member_count=count_result.scalar_one(),
        is_owner=league.owner_user_id == user_id,
    )


@router.post("", response_model=MiniLeagueOut, status_code=status.HTTP_201_CREATED)
async def create_league(
    body: MiniLeagueCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = await _generate_code(db)
    league = MiniLeague(name=body.name.strip(), code=code, season_id=body.season_id, owner_user_id=user.id)
    db.add(league)
    await db.flush()
    db.add(MiniLeagueMember(league_id=league.id, user_id=user.id))
    await db.commit()
    await db.refresh(league)
    return await _to_out(league, db, user.id)


@router.post("/join", response_model=MiniLeagueOut)
async def join_league(
    body: MiniLeagueJoin,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MiniLeague).where(MiniLeague.code == body.code.strip().upper()))
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(404, "Лига с таким кодом не найдена")

    existing = await db.execute(
        select(MiniLeagueMember).where(
            MiniLeagueMember.league_id == league.id, MiniLeagueMember.user_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Вы уже состоите в этой лиге")

    db.add(MiniLeagueMember(league_id=league.id, user_id=user.id))
    await db.commit()
    return await _to_out(league, db, user.id)


@router.get("/my", response_model=list[MiniLeagueOut])
async def my_leagues(
    season_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MiniLeague)
        .join(MiniLeagueMember, MiniLeagueMember.league_id == MiniLeague.id)
        .where(MiniLeagueMember.user_id == user.id, MiniLeague.season_id == season_id)
        .order_by(MiniLeague.created_at.desc())
    )
    leagues = result.scalars().all()
    return [await _to_out(l, db, user.id) for l in leagues]


@router.get("/{league_id}/standings", response_model=MiniLeagueStandingsOut)
async def league_standings(
    league_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    league = await db.get(MiniLeague, league_id)
    if not league:
        raise HTTPException(404, "Лига не найдена")

    member_result = await db.execute(
        select(MiniLeagueMember).where(
            MiniLeagueMember.league_id == league_id, MiniLeagueMember.user_id == user.id
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(403, "Вы не состоите в этой лиге")

    rows = await db.execute(
        select(User.id, User.username, FantasyTeam.name, FantasyTeam.total_points)
        .select_from(MiniLeagueMember)
        .join(User, User.id == MiniLeagueMember.user_id)
        .outerjoin(
            FantasyTeam,
            (FantasyTeam.user_id == User.id) & (FantasyTeam.season_id == league.season_id),
        )
        .where(MiniLeagueMember.league_id == league_id)
        .order_by(FantasyTeam.total_points.desc().nulls_last(), User.username)
    )
    standings = [
        MiniLeagueStandingEntry(
            rank=i + 1,
            user_id=uid,
            username=username,
            team_name=team_name,
            total_points=total_points or 0,
            is_me=uid == user.id,
        )
        for i, (uid, username, team_name, total_points) in enumerate(rows.all())
    ]
    return MiniLeagueStandingsOut(league=await _to_out(league, db, user.id), standings=standings)


@router.post("/{league_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_league(
    league_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MiniLeagueMember).where(
            MiniLeagueMember.league_id == league_id, MiniLeagueMember.user_id == user.id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Вы не состоите в этой лиге")
    await db.delete(member)
    await db.commit()
