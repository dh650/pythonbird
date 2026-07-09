from __future__ import annotations
import sqlite3
from pathlib import Path


class ThunderbirdContacts:
    def __init__(self, tb_instance: ThunderbirdLinux):
        self.profile_dir = tb_instance.profile_dir

    def get_all_contacts(self) -> list:
        """Extracts contact names and emails from abook.sqlite."""
        db_path = self.profile_dir / "abook.sqlite"
        if not db_path.exists():
            return []

        contacts = []
        # Connect in read-only mode to prevent database locks
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        try:
            # Thunderbird stores main contacts in the 'cards' table
            cursor.execute(
                "SELECT displayName, primaryEmail FROM cards WHERE primaryEmail IS NOT NULL"
            )
            for row in cursor.fetchall():
                contacts.append({"name": row[0], "email": row[1]})
        except sqlite3.OperationalError:
            # Fallback or handling if table schema changes
            pass
        finally:
            conn.close()

        return contacts
