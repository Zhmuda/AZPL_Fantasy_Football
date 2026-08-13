"""
Seeds N demo fantasy-football users with real, rule-valid squads, so a fresh
deployment has a populated leaderboard instead of looking empty for the
first real visitors.

Run inside the backend container (needs app.* imports + DB access):
    docker compose exec backend python scripts/seed_demo_users.py
    docker compose exec backend python scripts/seed_demo_users.py --count 30
    docker compose exec backend python scripts/seed_demo_users.py --count 10 --dry-run
    docker compose exec backend python scripts/seed_demo_users.py --undo

Demo accounts created:
    email:    <random username>@azpl-demo.local
    username: e.g. "elvin_23", "aysel_bk", "tural94" — varied first-name +
              suffix combos, not a giveaway sequential pattern
    password: Demo12345!   (same for all — throwaway seed accounts, not
                             meant to be handed out; the site owner can log
                             into any of them to poke around)

Talks to the DB directly via the same models/password hashing the API uses
(bypasses the public /auth/register HTTP endpoint on purpose — that one is
rate-limited to 5/hour per IP, which 30 signups would blow through). Squads
are built respecting the real game rules (budget, position quota, 3-per-club
cap) so they're indistinguishable from a squad a real player put together.

Every demo account's email ends in @azpl-demo.local (never user-visible —
only usernames/team names are shown in the UI) — that's the internal marker
used to find and remove them again with --undo, independent of whatever
username/team-name text happens to be on any given run.
Safe to re-run without --undo too: username collisions (against ALL users,
not just past demo runs) are skipped, never duplicated.
"""
import argparse
import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.security import hash_password
from app.core.content_filter import contains_banned_content
from app.models.user import User
from app.models.league import Season, Round, Player
from app.models.fantasy import FantasyTeam, FantasyPick

PASSWORD = "Demo12345!"
EMAIL_DOMAIN = "azpl-demo.local"

FORMATIONS = {
    "4-4-2": {"G": 1, "D": 4, "M": 4, "F": 2},
    "4-3-3": {"G": 1, "D": 4, "M": 3, "F": 3},
    "5-2-3": {"G": 1, "D": 5, "M": 2, "F": 3},
}
POS_QUOTA = {"G": 2, "D": 5, "M": 5, "F": 3}
BUDGET = 100.0
CLUB_LIMIT = 3
MAX_SQUAD_ATTEMPTS = 300

# First names used to build usernames — mixed male/female, Azerbaijani-
# flavored (Latin transliteration, matching how usernames actually look on
# this site) so they blend in rather than reading as a generated batch.
FIRST_NAMES = [
    "elvin", "tural", "kamran", "rashad", "farid", "orkhan", "murad", "ilkin",
    "anar", "vusal", "elshan", "samir", "fuad", "nihad", "ceyhun", "ramin",
    "vugar", "nicat", "emin", "rustam", "aydin", "elnur", "kanan", "toghrul",
    "bakhtiyar", "namig", "shahin", "zaur", "huseyn", "mehman",
    "aysel", "nigar", "leyla", "gunel", "aygun", "sevinj", "nermin",
    "zeynab", "konul", "aytaj",
]

# Several different username "shapes" — a random mix of these across users
# avoids the single-template look of e.g. "manager01".."manager30".
USERNAME_STYLES = [
    lambda name: f"{name}{random.randint(10, 99)}",
    lambda name: f"{name}_{random.randint(10, 99)}",
    lambda name: f"{name}_{random.choice(['fc', 'bk', 'az', 'baku'])}",
    lambda name: f"{name}{random.choice(['92', '95', '97', '99', '01', '03'])}",
    lambda name: name,
]

# Team names — deliberately not built from one adjective+noun template:
# a mix of local flavour, football-culture in-jokes, and personal-name
# styles, so 30 random picks read like 30 different people, not one script.
TEAM_NAMES = [
    "Тени Каспия", "Бакинский десант", "Последний рубеж", "Взгляд с трибуны",
    "На флажке", "Скамейка мечты", "Финальный свисток", "Три очка не просто так",
    "Голова кругом", "Вне игры", "Дворовая команда", "Хавбек и точка",
    "Атака с фланга", "Свободный удар", "Экстра-тайм", "Без замен",
    "Второй тайм", "Ва-банк", "Тактика без плана", "Ставка сделана",
    "Красно-белые мечты", "Синий вираж", "Дерби окраины", "Кубковая лихорадка",
    "Проходной балл", "На вылет", "Сборная подъезда", "Легенды района",
    "Азарт и удача", "Мяч в девятку", "Верхний угол", "Пас в разрез",
    "Контрольный выстрел", "Дубль в конце", "Огни Баку", "Каспийский бриз",
    "Nur FC", "Xəzər Ordusu", "28 May United", "Bakı Aslanları",
    "Neftçi Ruhu", "Qarabağ Dostları", "Zafər FC", "Dəniz Kənarı",
]


def generate_usernames(n: int, existing: set[str]) -> list[str]:
    names = FIRST_NAMES[:]
    random.shuffle(names)
    usernames: list[str] = []
    for name in names:
        if len(usernames) == n:
            break
        style = random.choice(USERNAME_STYLES)
        candidate = style(name)
        attempts = 0
        while (candidate in existing or candidate in usernames) and attempts < 10:
            candidate = f"{name}{random.randint(100, 999)}"
            attempts += 1
        if candidate not in existing and candidate not in usernames:
            usernames.append(candidate)
    return usernames


def generate_team_names(n: int) -> list[str]:
    names = TEAM_NAMES[:]
    random.shuffle(names)
    picked = names[:n]
    # Sanity check — the curated word list shouldn't ever trip the filter,
    # but if a future edit to it does, fail loudly instead of silently
    # sending a name the real /teams endpoint would reject.
    bad = [name for name in picked if contains_banned_content(name)]
    if bad:
        raise RuntimeError(f"Generated team name(s) failed the content filter: {bad}")
    return picked


def build_squad(players_by_pos: dict[str, list[Player]]) -> list[Player] | None:
    """Random valid 15-player squad: quota per position, <=CLUB_LIMIT per
    club, total price <= BUDGET. Retries with a fresh random draw rather
    than repairing one — with real price data the budget is comfortably
    achievable, so a handful of retries reliably finds a valid one."""
    for _ in range(MAX_SQUAD_ATTEMPTS):
        squad: list[Player] = []
        club_counts: dict[int, int] = {}
        feasible = True

        for pos, quota in POS_QUOTA.items():
            pool = players_by_pos[pos][:]
            random.shuffle(pool)
            picked = []
            for p in pool:
                if len(picked) == quota:
                    break
                club = p.team_id
                if club and club_counts.get(club, 0) >= CLUB_LIMIT:
                    continue
                picked.append(p)
                if club:
                    club_counts[club] = club_counts.get(club, 0) + 1
            if len(picked) < quota:
                feasible = False
                break
            squad.extend(picked)

        if feasible and sum(p.price for p in squad) <= BUDGET:
            return squad

    return None


def pick_formation_and_slots(squad: list[Player]) -> tuple[str, dict[int, int]]:
    """Picks a formation the squad's position mix can fill, then returns
    {player_id: slot} — slots 1-11 are starters, 12-15 the bench."""
    by_pos: dict[str, list[Player]] = {"G": [], "D": [], "M": [], "F": []}
    for p in squad:
        by_pos[p.position].append(p)
    for players in by_pos.values():
        random.shuffle(players)

    formation = random.choice(list(FORMATIONS.keys()))
    fmt = FORMATIONS[formation]

    slots: dict[int, int] = {}
    slot_no = 1
    bench: list[Player] = []
    for pos in ["G", "D", "M", "F"]:
        starters = by_pos[pos][: fmt[pos]]
        bench.extend(by_pos[pos][fmt[pos] :])
        for p in starters:
            slots[p.id] = slot_no
            slot_no += 1
    for p in bench:
        slots[p.id] = slot_no
        slot_no += 1

    return formation, slots


async def undo() -> None:
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        demo_user_ids = (
            (await db.execute(select(User.id).where(User.email.like(f"%@{EMAIL_DOMAIN}"))))
            .scalars()
            .all()
        )
        if not demo_user_ids:
            print("Демо-аккаунтов не найдено — удалять нечего.")
            return

        demo_team_ids = (
            (await db.execute(select(FantasyTeam.id).where(FantasyTeam.user_id.in_(demo_user_ids))))
            .scalars()
            .all()
        )

        await db.execute(delete(FantasyPick).where(FantasyPick.fantasy_team_id.in_(demo_team_ids)))
        await db.execute(delete(FantasyTeam).where(FantasyTeam.id.in_(demo_team_ids)))
        await db.execute(delete(User).where(User.id.in_(demo_user_ids)))
        await db.commit()

        print(f"Удалено: {len(demo_user_ids)} пользователей, {len(demo_team_ids)} команд (и все их пики).")


async def seed(count: int, dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        season = (await db.execute(select(Season).where(Season.is_active == True))).scalar_one_or_none()
        if not season:
            print("Нет активного сезона — нечего сидировать.")
            return

        rounds = (
            (await db.execute(select(Round).where(Round.season_id == season.id).order_by(Round.number)))
            .scalars()
            .all()
        )
        current_round = next((r for r in rounds if r.status != "finished"), rounds[-1] if rounds else None)
        if not current_round:
            print("В активном сезоне нет туров — нечего сидировать.")
            return

        players = (
            (await db.execute(select(Player).where(Player.is_active == True)))
            .scalars()
            .all()
        )
        players_by_pos: dict[str, list[Player]] = {"G": [], "D": [], "M": [], "F": []}
        for p in players:
            if p.position in players_by_pos:
                players_by_pos[p.position].append(p)
        missing = [pos for pos, quota in POS_QUOTA.items() if len(players_by_pos[pos]) < quota]
        if missing:
            print(f"Недостаточно игроков по позициям {missing} — нечего сидировать.")
            return

        existing_usernames = set(
            (await db.execute(select(User.username))).scalars().all()
        )

        usernames = generate_usernames(count, existing_usernames)
        team_names = generate_team_names(len(usernames))
        created = 0
        skipped = count - len(usernames)

        for username, team_name in zip(usernames, team_names):
            squad = build_squad(players_by_pos)
            if not squad:
                print(f"  ! {username}: не удалось собрать состав в рамках бюджета, пропуск")
                continue

            formation, slots = pick_formation_and_slots(squad)
            starters = [p for p in squad if slots[p.id] <= 11]
            captain, vice_captain = random.sample(starters, 2)

            email = f"{username}@{EMAIL_DOMAIN}"

            if dry_run:
                total_price = sum(p.price for p in squad)
                print(f"  [dry-run] {username} / \"{team_name}\" / {formation} / £{total_price:.1f}m")
                created += 1
                continue

            user = User(email=email, username=username, password_hash=hash_password(PASSWORD))
            db.add(user)
            await db.flush()  # need user.id for the team FK

            team = FantasyTeam(user_id=user.id, season_id=season.id, name=team_name)
            db.add(team)
            await db.flush()  # need team.id for the picks FK

            for p in squad:
                db.add(FantasyPick(
                    fantasy_team_id=team.id,
                    player_id=p.id,
                    round_id=current_round.id,
                    slot=slots[p.id],
                    is_captain=(p.id == captain.id),
                    is_vice_captain=(p.id == vice_captain.id),
                ))

            created += 1
            print(f"  + {username} / \"{team_name}\" / {formation}")

        if not dry_run:
            await db.commit()

        print(f"\nГотово: создано {created}, пропущено (нет свободных имён) {skipped}.")
        if created and not dry_run:
            print(f"Пароль у всех демо-аккаунтов: {PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=30, help="Сколько демо-пользователей создать (по умолчанию 30)")
    parser.add_argument("--dry-run", action="store_true", help="Ничего не пишет в БД, только показывает, что было бы создано")
    parser.add_argument("--undo", action="store_true", help="Удалить всех ранее созданных этим скриптом демо-пользователей вместе с их командами")
    args = parser.parse_args()

    if args.undo:
        asyncio.run(undo())
        sys.exit(0)

    if args.count > len(TEAM_NAMES) or args.count > len(FIRST_NAMES):
        print(f"--count не может быть больше {min(len(TEAM_NAMES), len(FIRST_NAMES))} (кончатся уникальные имена)")
        sys.exit(1)

    asyncio.run(seed(args.count, args.dry_run))
