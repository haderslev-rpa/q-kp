from __future__ import annotations

from dataclasses import asdict
from typing import Any

from q_kp.api.client import KpApiClient
from q_kp.models import KpHistorikPost, KpPensionstypePost
from q_kp.utils import validate_uuid


class KpPensionsfaktaApi:
    """API-kald til historikken under KP's Pensionsfakta."""

    def __init__(self, api_client: KpApiClient) -> None:
        self.api_client = api_client

    async def hent_pensionstype(self, person_id: str) -> list[KpPensionstypePost]:
        return [KpPensionstypePost.from_api(post) for post in await self._hent_historik(person_id, "pensionstype")]

    async def hent_formue(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "formue")

    async def hent_personlig_tillaegsprocent(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "personligTillaegsprocent")

    async def hent_helbredstillaegsprocent(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "helbredstillaegsprocent")

    async def hent_optjent_pensionsandel(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "broekprocent")

    async def hent_udenlandsk_pension(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "udenlandskpension")

    async def hent_maanedligt_fradrag(self, person_id: str) -> list[KpHistorikPost]:
        return await self._hent_standard_historik(person_id, "maanedligtfradrag")

    async def hent_aktuel_bevillingsdato(self, person_id: str) -> str | None:
        aktuel = self.find_aktuel_pensionstype(await self.hent_pensionstype(person_id))
        return aktuel.tilkendelsesdato if aktuel else None

    async def hent_alle_pensionsfakta(self, person_id: str) -> dict[str, Any]:
        pensionstype = await self.hent_pensionstype(person_id)
        aktuel = self.find_aktuel_pensionstype(pensionstype)
        return {
            "pensionstype": [asdict(post) for post in pensionstype],
            "aktuel_bevillingsdato": aktuel.tilkendelsesdato if aktuel else None,
            "formue": [asdict(post) for post in await self.hent_formue(person_id)],
            "personlig_tillaegsprocent": [asdict(post) for post in await self.hent_personlig_tillaegsprocent(person_id)],
            "helbredstillaegsprocent": [asdict(post) for post in await self.hent_helbredstillaegsprocent(person_id)],
            "optjent_pensionsandel": [asdict(post) for post in await self.hent_optjent_pensionsandel(person_id)],
            "udenlandsk_pension": [asdict(post) for post in await self.hent_udenlandsk_pension(person_id)],
            "maanedligt_fradrag": [asdict(post) for post in await self.hent_maanedligt_fradrag(person_id)],
        }

    @staticmethod
    def find_nyeste_post(historik: list[KpHistorikPost]) -> KpHistorikPost | None:
        if not historik:
            return None
        med_index = [post for post in historik if post.index is not None and post.index.isdigit()]
        return max(med_index, key=lambda post: int(post.index)) if med_index else historik[0]

    @staticmethod
    def find_aktuel_pensionstype(historik: list[KpPensionstypePost]) -> KpPensionstypePost | None:
        if not historik:
            return None
        aktive = [post for post in historik if (post.status or "").casefold() == "aktiv"]
        kandidater = aktive or historik
        aabne = [post for post in kandidater if post.gyldigtil in (None, "31-12-9999")]
        return max(aabne or kandidater, key=lambda post: KpPensionsfaktaApi._dato_noegle(post.gyldigfra))

    async def _hent_standard_historik(self, person_id: str, historiknavn: str) -> list[KpHistorikPost]:
        return [KpHistorikPost.from_api(post) for post in await self._hent_historik(person_id, historiknavn)]

    async def _hent_historik(self, person_id: str, historiknavn: str) -> list[dict[str, Any]]:
        person_id = validate_uuid(person_id, "person_id")
        result = await self.api_client.get(f"rest/api/person/history/{person_id}/{historiknavn}")
        if not isinstance(result, list):
            raise RuntimeError(f"Pensionsfakta '{historiknavn}' returnerede et uventet format.")
        return [post for post in result if isinstance(post, dict)]

    @staticmethod
    def _dato_noegle(value: str | None) -> tuple[int, int, int]:
        if not value:
            return (0, 0, 0)
        try:
            dag, maaned, aar = value.split("-")
            return (int(aar), int(maaned), int(dag))
        except (ValueError, AttributeError):
            return (0, 0, 0)
