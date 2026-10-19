from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID


def normalize_cpr(cpr: str) -> str:
    if not isinstance(cpr, str):
        raise TypeError("cpr skal være tekst.")
    value = "".join(character for character in cpr if character.isdigit())
    if len(value) != 10:
        raise ValueError("CPR skal bestå af præcis 10 cifre.")
    return value


def validate_uuid(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} skal være en ikke-tom tekst.")
    try:
        return str(UUID(value.strip()))
    except ValueError as error:
        raise ValueError(f"{field_name} skal være et gyldigt UUID.") from error


def iso_date(value: str | date | datetime, field_name: str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError as error:
            raise ValueError(f"{field_name} skal have formatet yyyy-mm-dd.") from error
    raise TypeError(f"{field_name} skal være tekst, date eller datetime.")


def utc_midnight(value: str | date | datetime, field_name: str) -> str:
    parsed = date.fromisoformat(iso_date(value, field_name))
    moment = datetime.combine(parsed, datetime.min.time(), tzinfo=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def validate_period(start: str, slut: str) -> None:
    if date.fromisoformat(start) > date.fromisoformat(slut):
        raise ValueError("startdato må ikke ligge efter slutdato.")
