"""Blocks obvious profanity / hate speech in user-chosen public text
(team names, usernames, mini-league names).

This is a deliberately simple filter, not a full moderation system: it
catches casual abuse cheaply and with zero external dependencies, but won't
catch creative obfuscation (extra spacing between letters of a whole-word
slur, unicode look-alikes) and can still occasionally miss/false-positive.
Anything that slips through — or gets wrongly blocked — is fixed by hand via
the admin panel (UserAdmin / FantasyTeamAdmin / MiniLeagueAdmin all support
editing the name directly).

Two tiers, split by false-positive risk:
- _SUBSTRING_ROOTS: distinctive enough to match anywhere in the text (also
  catches spaced-out obfuscation, e.g. "х у й", since spaces are stripped
  before this check). Mostly profanity roots that don't occur inside
  ordinary words.
- _EXACT_WORDS: short/ambiguous roots that collide with real words if
  matched as a substring (e.g. "жид" inside "жидкость", "хач" inside
  "хачапури", "got" inside any English sentence) — matched only when a
  whitespace-split token equals one of these exactly.
"""
import re
import unicodedata

_SUBSTRING_ROOTS = {
    # Russian profanity (common roots — catches most inflected forms)
    "хуй", "хуе", "хуё", "хуя", "хуи",
    "пизд", "пздц",
    "ебат", "ебал", "ебан", "ебуч", "ебл", "заеб", "наеб", "объеб", "уеб", "выеб",
    "бляд", "блят",
    "мудак", "мудил",
    "залуп",
    "гандон", "гондон",
    "пидор", "пидар", "педик",
    "долбоеб", "долбоёб",
    "сволоч",
    "ублюд",
    # Russian nationalist/hate terms (distinctive, low collision risk)
    "нацист", "фашист", "фашизм", "черножоп",

    # English profanity
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "whore",
    "slut", "motherfuck",
    # English nationalist/hate terms
    "nigger", "nigga", "chink", "faggot",
    "nazi", "hitler", "whitepower", "1488",

    # Azerbaijani profanity
    "siktir", "qehbe", "qəhbə", "orospu", "amcik", "amcıq",
}

# Ambiguous roots that are real words/names when embedded in something
# longer — only flagged as a standalone token (see module docstring).
_EXACT_WORDS = {
    "жид", "жиды", "жида", "жидов", "жидовский", "жидовская",
    "хач", "хачи", "хачей", "хача",
    "чурка", "чурки", "чурок",
    "негр", "негры", "негра", "негров", "негроид",
    "хохол", "хохлы", "хохла", "хохлов",
    "москаль", "москали", "москаля",
    "сука", "суки", "суку",
    "наци", "kkk",
}

# Common leetspeak / lookalike substitutions collapsed to a canonical letter
# before matching, so basic digit/symbol swaps ("h3ll0") are still caught.
_SUBSTITUTIONS = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s", "!": "i",
})


def _normalize_word(word: str) -> str:
    word = unicodedata.normalize("NFKC", word).lower().translate(_SUBSTITUTIONS)
    word = word.replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]", "", word)


def contains_banned_content(text: str) -> bool:
    """True if `text` contains a profane/hateful root once normalized."""
    words = [_normalize_word(w) for w in text.split() if w]
    if any(w in _EXACT_WORDS for w in words):
        return True

    joined = "".join(words)
    return any(root in joined for root in _SUBSTRING_ROOTS)
