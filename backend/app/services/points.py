"""Fantasy points calculation rules."""

SCORING: dict[str, int | dict[str, int]] = {
    "minutes_1_59": 1,
    "minutes_60_plus": 2,
    "goal": {"G": 6, "D": 6, "M": 5, "F": 4},
    "assist": 3,
    "clean_sheet": {"G": 4, "D": 4, "M": 1, "F": 0},
    "saves_per_3": 1,
    "penalty_save": 5,
    "penalty_miss": -2,
    "yellow_card": -1,
    "red_card": -3,
    "own_goal": -2,
}


def calc_points(
    position: str,
    minutes_played: int,
    goals: int,
    assists: int,
    yellow_cards: int,
    red_cards: int,
    saves: int,
    own_goals: int,
    penalty_miss: int,
    penalty_save: int,
    clean_sheet: bool,
) -> int:
    pts = 0

    if minutes_played >= 60:
        pts += SCORING["minutes_60_plus"]
    elif minutes_played > 0:
        pts += SCORING["minutes_1_59"]

    pts += goals * SCORING["goal"][position]
    pts += assists * SCORING["assist"]
    pts += (saves // 3) * SCORING["saves_per_3"]
    pts += penalty_save * SCORING["penalty_save"]
    pts += penalty_miss * SCORING["penalty_miss"]
    pts += yellow_cards * SCORING["yellow_card"]
    pts += red_cards * SCORING["red_card"]
    pts += own_goals * SCORING["own_goal"]

    if clean_sheet and minutes_played >= 60:
        pts += SCORING["clean_sheet"][position]

    return pts
