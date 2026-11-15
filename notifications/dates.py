"""Russian plural forms and relative day labels for deadlines."""

from datetime import date


def ru_plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def relative_day_label(day: date, today: date) -> str:
    delta = (day - today).days
    if delta < 0:
        return "срок прошёл"
    if delta == 0:
        return "сегодня"
    if delta == 1:
        return "завтра"
    return f"через {delta} {ru_plural(delta, 'день', 'дня', 'дней')}"
