import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_filter import contains_banned_content
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.schemas.user import (
    UserRegister, UserLogin, UserOut, Token, PasswordChange,
    PasswordResetRequest, PasswordResetConfirm,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Excludes visually ambiguous characters (0/O, 1/I/L) — the site owner reads
# this out of the admin panel and relays it to the user manually.
RESET_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")
RESET_CODE_TTL_HOURS = 24


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(request: Request, body: UserRegister, db: AsyncSession = Depends(get_db)):
    if contains_banned_content(body.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Имя пользователя содержит недопустимые слова")

    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email or username already taken")

    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
async def change_password(
    request: Request,
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Текущий пароль неверен")
    user.password_hash = hash_password(body.new_password)
    await db.commit()


@router.post("/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/hour")
async def request_password_reset(request: Request, body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """No email delivery on this project — the code just lands on the user's
    row in the admin panel for the site owner to relay manually. Always
    returns 204 either way so this can't be used to enumerate registered
    emails."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        user.reset_code = "".join(secrets.choice(RESET_CODE_ALPHABET) for _ in range(6))
        user.reset_code_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=RESET_CODE_TTL_HOURS)
        await db.commit()


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
async def confirm_password_reset(request: Request, body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if (
        not user
        or not user.reset_code
        or user.reset_code != body.code.strip().upper()
        or not user.reset_code_expires
        or user.reset_code_expires < now
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный или просроченный код")

    user.password_hash = hash_password(body.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    await db.commit()
