def short_vnd(v: int | float | None) -> str:
    """2200000 -> '2,2 triệu'; 900000 -> '900 nghìn'."""
    if v is None:
        return "—"
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") + " triệu"
    return f"{round(v / 1000):d} nghìn"


def full_vnd(v: int | float | None) -> str:
    if v is None:
        return "—"
    return f"{int(round(v)):,}".replace(",", ".") + "đ"


def parse_number(s: str) -> float:
    return float(s.replace(",", "."))
