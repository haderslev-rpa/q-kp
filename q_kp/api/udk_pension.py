from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from q_kp.api.client import KpApiClient
from q_kp.utils import iso_date, validate_period, validate_uuid


@dataclass(frozen=True, slots=True)
class KpUdkUdbetalingsraekke:
    navn: str | None
    vaerdier: list[str]


@dataclass(frozen=True, slots=True)
class KpUdkUdbetalingsoversigt:
    """Valideret UDK-svar.

    API'et deler tabellen i datooverskrifter, rækkenavne og datarækker.
    KP viser de samme data som én tabel. som_visningstabel() samler delene.
    """

    dispositionsdatoer: list[str]
    raekker: list[KpUdkUdbetalingsraekke]
    sidste_kolonnevaerdier: Any
    fejlbeskeder: Any

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "KpUdkUdbetalingsoversigt":
        datoer = value.get("columnDateHeaders")
        navne = value.get("topTableRowNames")
        data = value.get("topTableData")
        if not isinstance(datoer, list) or not isinstance(navne, list) or not isinstance(data, list):
            raise RuntimeError("UDK-svaret mangler en eller flere tabel-lister.")
        if len(navne) != len(data):
            raise RuntimeError("UDK-svaret har forskelligt antal rækkenavne og datarækker.")
        raekker = []
        for indeks, (navn, dataraekke) in enumerate(zip(navne, data, strict=True)):
            if not isinstance(dataraekke, dict) or not isinstance(dataraekke.get("row"), list):
                raise RuntimeError(f"UDK-datarække {indeks} har et uventet format.")
            row = dataraekke["row"]
            if len(row) != len(datoer):
                raise RuntimeError(f"UDK-datarække {indeks} passer ikke med antal datoer.")
            raekker.append(KpUdkUdbetalingsraekke(
                navn=None if navn is None else str(navn),
                vaerdier=[str(element) for element in row],
            ))
        return cls(
            dispositionsdatoer=[str(element) for element in datoer],
            raekker=raekker,
            sidste_kolonnevaerdier=value.get("topTableLastColumnValues"),
            fejlbeskeder=value.get("errorMessages"),
        )

    def som_visningstabel(self) -> list[dict[str, str | None]]:
        tabel = []
        for raekke in self.raekker:
            visningsraekke: dict[str, str | None] = {"raekke": raekke.navn}
            visningsraekke.update(dict(zip(self.dispositionsdatoer, raekke.vaerdier, strict=True)))
            tabel.append(visningsraekke)
        return tabel


class KpUdkPensionApi:
    def __init__(self, api_client: KpApiClient) -> None:
        self.api_client = api_client

    async def hent_udbetalingsoversigt(
        self,
        person_id: str,
        startdato: str | date | datetime,
        slutdato: str | date | datetime,
    ) -> KpUdkUdbetalingsoversigt:
        """Hent UDK-tabellen og saml JSON-delene til en valideret model."""
        person_id = validate_uuid(person_id, "person_id")
        start = iso_date(startdato, "startdato")
        slut = iso_date(slutdato, "slutdato")
        validate_period(start, slut)
        result = await self.api_client.post(
            f"rest/api/person/udbetalingerudk/{person_id}/list",
            json_body={"startDate": start, "stopDate": slut},
        )
        if not isinstance(result, dict):
            raise RuntimeError("Udbetalingsoversigt - UDK returnerede et uventet format.")
        return KpUdkUdbetalingsoversigt.from_api(result)
