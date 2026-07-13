from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union


@dataclass(frozen=True)
class Attachment:
    """An attachment extracted from an email message."""

    filename: str
    content_type: str
    data: bytes = field(repr=False)

    @property
    def size(self) -> int:
        return len(self.data)

    def save(self, destination: Union[Path, str], overwrite: bool = False) -> Path:
        path = Path(destination).expanduser()
        if path.exists() and path.is_dir():
            path = path / self.filename
        elif not path.suffix and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            path = path / self.filename

        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists() and not overwrite:
            raise FileExistsError(f"Attachment already exists: {path}")

        path.write_bytes(self.data)
        return path


@dataclass(frozen=True)
class Message:
    """A parsed Thunderbird email message."""

    id: Any
    sender: str
    recipients: str
    subject: str
    date: str
    text_body: str = ""
    html_body: str = ""
    attachments: tuple[Attachment, ...] = ()
    raw_bytes: Optional[bytes] = field(default=None, repr=False, compare=False)

    @property
    def body(self) -> str:
        return self.text_body or self.html_body

    def to_dict(self) -> dict[str, Any]:
        """Return the legacy dictionary representation used by v0.1.x."""
        return {
            "id": self.id,
            "from": self.sender,
            "to": self.recipients,
            "subject": self.subject,
            "date": self.date,
            "body": self.body,
            "text_body": self.text_body,
            "html_body": self.html_body,
            "attachments": list(self.attachments),
        }

    def save_eml(self, destination: Union[Path, str], overwrite: bool = False) -> Path:
        if self.raw_bytes is None:
            raise ValueError("Raw message data is not available.")

        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists() and not overwrite:
            raise FileExistsError(f"Message file already exists: {path}")

        path.write_bytes(self.raw_bytes)
        return path


@dataclass(frozen=True)
class Contact:
    """A contact stored in a Thunderbird address book."""

    name: str
    email: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email}
