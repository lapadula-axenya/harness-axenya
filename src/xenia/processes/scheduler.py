"""Cron scheduling helpers — parsing, next-run computation, human labels."""
from __future__ import annotations

from datetime import datetime

from croniter import CroniterBadCronError, croniter


class InvalidCronError(ValueError):
    pass


def cron_validate(expression: str) -> None:
    if not expression or not expression.strip():
        raise InvalidCronError("cron expression is empty")
    try:
        croniter(expression.strip())
    except (CroniterBadCronError, KeyError, ValueError) as exc:
        raise InvalidCronError(f"invalid cron expression: {exc}") from exc


def cron_next(expression: str, *, after: datetime) -> datetime:
    cron_validate(expression)
    it = croniter(expression.strip(), after)
    ts: datetime = it.get_next(datetime)
    return ts


_DOW_PT = {
    0: "dom",
    1: "seg",
    2: "ter",
    3: "qua",
    4: "qui",
    5: "sex",
    6: "sáb",
    7: "dom",
}


def cron_describe(expression: str) -> str:
    """Best-effort human-readable label in pt-BR. Falls back to the cron string."""
    cron_validate(expression)
    parts = expression.strip().split()
    if len(parts) != 5:
        return expression
    minute, hour, dom, month, dow = parts

    def _every(field: str, unit: str) -> str | None:
        if field.startswith("*/"):
            return f"A cada {field[2:]}{unit}"
        return None

    bits: list[str] = []

    every_min = _every(minute, "min")
    every_hour = _every(hour, "h")

    if every_min and hour == "*":
        bits.append(every_min)
    elif minute == "0" and every_hour:
        bits.append(every_hour)
    elif every_min and "-" in hour:
        lo, hi = hour.split("-", 1)
        bits.append(f"{every_min}, {lo}h-{hi}h")
    elif minute.isdigit() and hour.isdigit():
        bits.append(f"{int(hour):02d}h{int(minute):02d}".rstrip("0").rstrip("h") if int(minute) == 0 else f"{int(hour)}h{int(minute):02d}")
        if int(minute) == 0:
            bits[-1] = f"{int(hour)}h"
    elif minute.isdigit() and "-" in hour and "/" in hour:
        # ex.: '0 8-18/2 * * 1-5'
        rng, step = hour.split("/", 1)
        lo, hi = rng.split("-", 1)
        bits.append(f"A cada {step}h, {lo}h-{hi}h")
    elif minute.isdigit() and "-" in hour:
        lo, hi = hour.split("-", 1)
        bits.append(f"{lo}h-{hi}h")
    elif minute == "0" and hour.isdigit():
        bits.append(f"Diariamente às {int(hour)}h")

    if dom != "*" and month == "*":
        try:
            bits.append(f"Dia {int(dom)} do mês")
        except ValueError:
            bits.append(f"Dia {dom} do mês")

    if dow != "*":
        if dow == "1-5":
            bits.append("seg-sex")
        else:
            try:
                bits.append(_DOW_PT[int(dow)])
            except (ValueError, KeyError):
                bits.append(dow)

    if not bits:
        return expression
    return ", ".join(bits)
