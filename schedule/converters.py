from datetime import date


class IsoDateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value: str) -> date:
        day = date.fromisoformat(value)
        if not date(2000, 1, 1) <= day <= date(2100, 12, 31):
            raise ValueError
        return day

    def to_url(self, value: date) -> str:
        return value.isoformat()
