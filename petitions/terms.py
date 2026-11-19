"""Russian wording of processing terms."""


def term_label(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return f"до {days} рабочего дня"
    return f"до {days} рабочих дней"
