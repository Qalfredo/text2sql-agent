from __future__ import annotations

from typing import Iterable

import requests

from .config import Settings
from .schema_docs import ColumnDoc


class CodaDocsClient:
    BASE_URL = "https://coda.io/apis/v1"

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.coda_api_token
            and self.settings.coda_doc_id
            and self.settings.coda_table_id_or_name
        )

    def load_docs(self) -> list[ColumnDoc]:
        if not self.enabled:
            return []

        headers = {"Authorization": f"Bearer {self.settings.coda_api_token}"}
        doc_id = self.settings.coda_doc_id
        table_id = self.settings.coda_table_id_or_name

        items: list[dict] = []
        page_token: str | None = None

        while True:
            params = {"useColumnNames": "true", "limit": 500}
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(
                f"{self.BASE_URL}/docs/{doc_id}/tables/{table_id}/rows",
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("items", []))

            next_link = payload.get("nextPageLink")
            if not next_link:
                break

            # Coda response includes pageToken in nextPageLink query string.
            if "pageToken=" not in next_link:
                break
            page_token = next_link.split("pageToken=", 1)[1].split("&", 1)[0]

        return list(self._parse_rows(items))

    def _parse_rows(self, rows: list[dict]) -> Iterable[ColumnDoc]:
        schema_col = self.settings.coda_schema_column
        table_col = self.settings.coda_table_column
        column_col = self.settings.coda_column_column
        desc_col = self.settings.coda_description_column

        for row in rows:
            values = row.get("values", {})
            table_name = str(values.get(table_col, "")).strip()
            description = str(values.get(desc_col, "")).strip()
            if not table_name or not description:
                continue

            schema_name_raw = values.get(schema_col)
            schema_name = str(schema_name_raw).strip() if schema_name_raw else None

            column_raw = values.get(column_col)
            column_name = str(column_raw).strip() if column_raw else None

            yield ColumnDoc(
                schema_name=schema_name or None,
                table_name=table_name,
                column_name=column_name or None,
                description=description,
            )
