from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union
from urllib.parse import quote

from .core import ThunderbirdLinux
from .models import Contact


class ThunderbirdContactsError(RuntimeError):
    """Raised when a Thunderbird address book cannot be read."""


class ThunderbirdContacts:
    def __init__(self, tb_instance: ThunderbirdLinux):
        self.profile_dir = tb_instance.profile_dir

    def get_all_contacts(
        self,
        database_path: Optional[Union[str, Path]] = None,
        strict: bool = True,
    ) -> list[dict]:
        if database_path is None:
            db_path = self.profile_dir / "abook.sqlite"
        else:
            db_path = Path(database_path).expanduser().resolve()

        if not db_path.is_file():
            return []

        try:
            return self._read_contacts(db_path)
        except sqlite3.Error as error:
            if not strict:
                return []

            raise ThunderbirdContactsError(
                f"Could not read Thunderbird address book: {db_path}"
            ) from error

    def get_contact_models(
        self,
        database_path: Optional[Union[str, Path]] = None,
        strict: bool = True,
    ) -> list[Contact]:
        """Return contacts as typed Contact objects."""
        return [
            Contact(name=item["name"], email=item["email"])
            for item in self.get_all_contacts(
                database_path=database_path,
                strict=strict,
            )
        ]

    def _read_contacts(self, db_path: Path) -> list[dict]:
        database_uri = f"file:{quote(str(db_path))}?mode=ro"

        with sqlite3.connect(database_uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row

            if not self._table_exists(connection, "cards"):
                raise ThunderbirdContactsError(
                    "The address book does not contain the expected " "'cards' table."
                )

            columns = self._get_table_columns(connection, "cards")

            required_columns = {
                "displayName",
                "primaryEmail",
            }

            missing_columns = required_columns - columns

            if missing_columns:
                missing_text = ", ".join(sorted(missing_columns))

                raise ThunderbirdContactsError(
                    "The Thunderbird address book schema is not supported. "
                    f"Missing columns: {missing_text}"
                )

            cursor = connection.execute(
                """
                SELECT displayName, primaryEmail
                FROM cards
                WHERE primaryEmail IS NOT NULL
                  AND TRIM(primaryEmail) != ''
                ORDER BY displayName COLLATE NOCASE
                """
            )

            contacts = []

            for row in cursor:
                name = row["displayName"] or ""
                email = row["primaryEmail"].strip()

                contacts.append(
                    {
                        "name": name,
                        "email": email,
                    }
                )

            return contacts

    @staticmethod
    def _table_exists(
        connection: sqlite3.Connection,
        table_name: str,
    ) -> bool:
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()

        return row is not None

    @staticmethod
    def _get_table_columns(
        connection: sqlite3.Connection,
        table_name: str,
    ) -> set[str]:
        cursor = connection.execute(f'PRAGMA table_info("{table_name}")')

        return {row["name"] for row in cursor}
