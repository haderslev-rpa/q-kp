from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class KpPerson:
    id: str
    cpr: str
    navn: str
    pensions_type: str
    beskyttelse: str
    name_address_protected: bool

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "KpPerson":
        return cls(
            id=str(value.get("id", "")),
            cpr=str(value.get("cpr", "")),
            navn=str(value.get("navn", "")),
            pensions_type=str(value.get("pensionsType", "")),
            beskyttelse=str(value.get("beskyttelse", "")),
            name_address_protected=bool(value.get("nameAddressProtected", False)),
        )


@dataclass(frozen=True, slots=True)
class KpSag:
    id: str
    titel: str
    sagstype: str
    bevilling_start: str | None
    bevilling_slut: str | None
    sagstilstand: str
    active: bool

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "KpSag":
        return cls(
            id=str(value.get("id", "")),
            titel=str(value.get("titel", "")),
            sagstype=str(value.get("sagstype", "")),
            bevilling_start=value.get("bevillingStart"),
            bevilling_slut=value.get("bevillingSlut"),
            sagstilstand=str(value.get("sagstilstand", "")),
            active=bool(value.get("active", False)),
        )


@dataclass(frozen=True, slots=True)
class KpHistorikPost:
    index: str | None
    vaerdi: str
    gyldigfra: str | None
    gyldigtil: str | None
    aendret: str | None
    adresse_type: str | None

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "KpHistorikPost":
        raw_index = value.get("index")
        return cls(
            index=None if raw_index is None else str(raw_index),
            vaerdi=str(value.get("vaerdi", "")),
            gyldigfra=value.get("gyldigfra"),
            gyldigtil=value.get("gyldigtil"),
            aendret=value.get("aendret"),
            adresse_type=value.get("adresseType"),
        )


@dataclass(frozen=True, slots=True)
class KpPensionstypePost(KpHistorikPost):
    tilkendelsesdato: str | None
    status: str | None

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "KpPensionstypePost":
        raw_index = value.get("index")
        return cls(
            index=None if raw_index is None else str(raw_index),
            vaerdi=str(value.get("vaerdi", "")),
            gyldigfra=value.get("gyldigfra"),
            gyldigtil=value.get("gyldigtil"),
            aendret=value.get("aendret"),
            adresse_type=value.get("adresseType"),
            tilkendelsesdato=value.get("tilkendelsesdato"),
            status=value.get("status"),
        )
