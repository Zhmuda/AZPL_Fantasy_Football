from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.league import Match, Round, Season, Team
from app.schemas.league import MatchOut, RoundOut, SeasonOut, TeamOut

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/teams", response_model=list[TeamOut])
async def get_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).order_by(Team.name))
    return result.scalars().all()


@router.get("/seasons", response_model=list[SeasonOut])
async def get_seasons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Season).order_by(Season.id.desc()))
    return result.scalars().all()


@router.get("/seasons/{season_id}/rounds", response_model=list[RoundOut])
async def get_rounds(season_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Round).where(Round.season_id == season_id).order_by(Round.number)
    )
    return result.scalars().all()


@router.get("/rounds/{round_id}", response_model=list[MatchOut])
async def get_round_matches(round_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.round_id == round_id)
        .order_by(Match.started_at)
    )
    return result.scalars().all()


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(404, "Match not found")
    return match
