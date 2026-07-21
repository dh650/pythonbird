from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Union

from .contacts import ThunderbirdContacts
from .core import ThunderbirdLinux
from .mail import ThunderbirdMail
from .models import Contact, Message


class Thunderbird:
    """High-level object-oriented interface to a Thunderbird profile."""

    def __init__(
        self,
        profile_dir: Optional[Union[str, Path]] = None,
        command: Optional[Sequence[str]] = None,
    ):
        self.client = ThunderbirdLinux(profile_dir=profile_dir, command=command)
        self.mail = ThunderbirdMail(self.client)
        self.address_book = ThunderbirdContacts(self.client)

    @property
    def profile_dir(self) -> Path:
        return self.client.profile_dir

    def accounts(self) -> list[str]:
        return self.client.get_mail_accounts()

    def folders(self) -> list[str]:
        return self.mail.list_folders()

    def messages(
        self, folder: Union[str, Path] = "Inbox", limit: Optional[int] = None
    ) -> list[Message]:
        return self.mail.get_messages(folder=folder, limit=limit)

    def search(self, folder: Union[str, Path] = "Inbox", **filters) -> list[Message]:
        return self.mail.search_messages(folder=folder, **filters)

    def iter_search(self, folder: Union[str, Path] = "Inbox", **filters):
        return self.mail.iter_search_messages(folder=folder, **filters)

    def contacts(self, database_path=None, strict: bool = True) -> list[Contact]:
        return self.address_book.get_contact_models(
            database_path=database_path, strict=strict
        )

    def compose(self, to: str, subject: str, body: str, attachment_path=None):
        return self.client.open_compose_window(
            to=to,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
        )

    def export_json(
        self,
        destination,
        folder: Union[str, Path] = "Inbox",
        limit: Optional[int] = None,
    ) -> Path:
        return self.mail.export_json(
            destination=destination, folder=folder, limit=limit
        )
