from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import engine
from app.api.v1 import auth, players, matches, fantasy, leagues
from app.admin.views import (
    UserAdmin, SeasonAdmin, RoundAdmin, TeamAdmin,
    PlayerAdmin, MatchAdmin, PlayerMatchStatAdmin, FantasyTeamAdmin,
    FantasyPickAdmin, FantasyRoundScoreAdmin, MatchEventAdmin,
    SystemSettingAdmin, SyncLogAdmin, MiniLeagueAdmin, MiniLeagueMemberAdmin,
)

ADMIN_SESSION_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        super().__init__(secret_key)
        # Base class hardcodes the session cookie's default 14-day max_age —
        # override it here to keep the admin logged in for 90 days.
        self.middlewares = [
            Middleware(SessionMiddleware, secret_key=secret_key, max_age=ADMIN_SESSION_MAX_AGE)
        ]

    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form.get("username") == "admin" and form.get("password") == settings.ADMIN_PASSWORD:
            request.session.update({"admin": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin", False)


app = FastAPI(
    title="AZPL Fantasy Football API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Admin panel at /admin
admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=settings.SECRET_KEY))
admin.add_view(UserAdmin)
admin.add_view(SeasonAdmin)
admin.add_view(RoundAdmin)
admin.add_view(TeamAdmin)
admin.add_view(PlayerAdmin)
admin.add_view(MatchAdmin)
admin.add_view(MatchEventAdmin)
admin.add_view(PlayerMatchStatAdmin)
admin.add_view(FantasyTeamAdmin)
admin.add_view(FantasyPickAdmin)
admin.add_view(FantasyRoundScoreAdmin)
admin.add_view(SystemSettingAdmin)
admin.add_view(SyncLogAdmin)
admin.add_view(MiniLeagueAdmin)
admin.add_view(MiniLeagueMemberAdmin)

# API routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(fantasy.router, prefix="/api/v1")
app.include_router(leagues.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
