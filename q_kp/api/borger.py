from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from q_kp.api.client import KpApiClient
from q_kp.models import KpPerson, KpSag
from q_kp.utils import iso_date, normalize_cpr, utc_midnight, validate_period, validate_uuid

Sagstype = Literal["aktiv", "inaktiv", "alle"]


class KpBorgerApi:
    """API-kald vedrørende en borger, borgerens sager og fanedata."""

    def __init__(self, api_client: KpApiClient) -> None:
        self.api_client = api_client

    async def fremsoeg_borger(self, cpr: str) -> list[KpPerson]:
        normalized_cpr = normalize_cpr(cpr)
        result = await self.api_client.post(
            "rest/api/search/person",
            json_body={
                "cpr": normalized_cpr,
                "navn": "",
                "pageSize": 10,
                "pageIndex": -1,
                "sortDirection": "",
                "sortField": "",
                "columnFilters": [],
            },
        )
        if not isinstance(result, dict) or not isinstance(result.get("personSearches", []), list):
            raise RuntimeError("Borgersøgningen returnerede et uventet format.")
        return [KpPerson.from_api(value) for value in result.get("personSearches", []) if isinstance(value, dict)]

    async def hent_borger(self, cpr: str) -> KpPerson:
        normalized_cpr = normalize_cpr(cpr)
        exact = [person for person in await self.fremsoeg_borger(normalized_cpr) if normalize_cpr(person.cpr) == normalized_cpr]
        if not exact:
            raise RuntimeError("Der blev ikke fundet en borger med det angivne CPR.")
        if len(exact) > 1:
            raise RuntimeError("KP returnerede flere borgere med samme CPR.")
        validate_uuid(exact[0].id, "person_id")
        return exact[0]

    async def naviger_til_borger(self, person_id: str) -> None:
        person_id = validate_uuid(person_id, "person_id")
        await self.api_client.navigate(f"person/{person_id}/overblik")

    async def hent_pensionsoplysninger(self, person_id: str) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        return await self.api_client.get(f"rest/api/person/overview/{person_id}/pensionsoplysninger")

    async def hent_helbredstillaegsprocent(
        self,
        person_id: str,
    ) -> list[dict[str, Any]]:
        """Hent historikken for borgerens helbredstillægsprocent.

        Metoden bevares på KpBorgerApi af hensyn til eksisterende tests og
        processer. Nye kald kan alternativt bruge
        KpPensionsfaktaApi.hent_helbredstillaegsprocent().
        """
        person_id = validate_uuid(
            person_id,
            "person_id",
        )

        result = await self.api_client.get(
            "rest/api/person/history/"
            f"{person_id}/helbredstillaegsprocent"
        )

        if not isinstance(result, list):
            raise RuntimeError(
                "Helbredstillægsprocent returnerede et uventet format."
            )

        return [
            value
            for value in result
            if isinstance(value, dict)
        ]

    async def hent_overblikshaendelser(self, person_id: str) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        return await self.api_client.get(f"rest/api/person/overview/{person_id}/haendelse")

    async def hent_sager(self, person_id: str, types: Sagstype = "aktiv") -> list[KpSag]:
        person_id = validate_uuid(person_id, "person_id")
        if types not in ("aktiv", "inaktiv", "alle"):
            raise ValueError("types skal være 'aktiv', 'inaktiv' eller 'alle'.")
        result = await self.api_client.get(f"rest/api/person/overview/{person_id}/sager", params={"types": types})
        if not isinstance(result, dict) or not isinstance(result.get("sags", []), list):
            raise RuntimeError("Sagsoversigten returnerede et uventet format.")
        return [KpSag.from_api(value) for value in result.get("sags", []) if isinstance(value, dict)]

    async def naviger_til_sag(self, person_id: str, sag_id: str) -> None:
        person_id = validate_uuid(person_id, "person_id")
        sag_id = validate_uuid(sag_id, "sag_id")
        await self.api_client.navigate(f"person/{person_id}/sag/{sag_id}/saginfo")

    async def hent_sagsinfo(self, sag_id: str) -> Any:
        sag_id = validate_uuid(sag_id, "sag_id")
        return await self.api_client.get(f"rest/api/sagoverview/sagsinfo/{sag_id}")

    async def hent_dokumenter(self, person_id: str, startdato: str | date | datetime, slutdato: str | date | datetime, *, page_size: int = 100) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        return await self.api_client.post(
            f"rest/api/person/dokumenter/{person_id}/searchDokumenter",
            json_body=self._periode_payload(startdato, slutdato, page_size=page_size, utc=True),
        )

    async def hent_journalnotater(self, person_id: str, startdato: str | date | datetime, slutdato: str | date | datetime, *, page_size: int = 100) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        return await self.api_client.post(
            f"rest/api/person/journalnotat/{person_id}/searchJournalnotat",
            json_body=self._periode_payload(startdato, slutdato, page_size=page_size, utc=True),
        )

    async def hent_indkomstoplysninger(self, person_id: str, startdato: str | date | datetime, slutdato: str | date | datetime) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        start = iso_date(startdato, "startdato")
        slut = iso_date(slutdato, "slutdato")
        validate_period(start, slut)
        return await self.api_client.post(
            f"rest/api/person/{person_id}/indkomstoplysninger",
            json_body={"startDate": start, "stopDate": slut},
        )

    async def hent_haendelser(self, person_id: str, startdato: str | date | datetime, slutdato: str | date | datetime, *, page_size: int = 100) -> Any:
        person_id = validate_uuid(person_id, "person_id")
        start = iso_date(startdato, "startdato")
        slut = iso_date(slutdato, "slutdato")
        validate_period(start, slut)
        return await self.api_client.post(
            f"rest/api/persondetails/{person_id}/haendelse",
            json_body={
                "columnFilters": [], "pageIndex": 0, "pageSize": page_size,
                "filteringCondition": "", "sortDirection": "desc", "sortField": "",
                "periodeEndDato": slut, "periodeStartDato": start,
            },
        )

    @staticmethod
    def _periode_payload(startdato: str | date | datetime, slutdato: str | date | datetime, *, page_size: int, utc: bool) -> dict[str, Any]:
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 1000:
            raise ValueError("page_size skal være mellem 1 og 1000.")
        start = iso_date(startdato, "startdato")
        slut = iso_date(slutdato, "slutdato")
        validate_period(start, slut)
        return {
            "columnFilters": [], "pageIndex": 0, "pageSize": page_size,
            "filteringCondition": "", "sortDirection": "desc", "sortField": "",
            "periodeSlutDato": utc_midnight(slut, "slutdato") if utc else slut,
            "periodeStartDato": utc_midnight(start, "startdato") if utc else start,
        }
