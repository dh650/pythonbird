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
    read: Optional[bool] = None
    starred: bool = False
    replied: bool = False
    forwarded: bool = False
    tags: tuple[str, ...] = ()
    raw_bytes: Optional[bytes] = field(default=None, repr=False, compare=False)

    @property
    def body(self) -> str:
        return self.text_body or self.html_body

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation compatible with v0.1.x."""
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
            "read": self.read,
            "starred": self.starred,
            "replied": self.replied,
            "forwarded": self.forwarded,
            "tags": list(self.tags),
        }

    def save_eml(self, destination: Union[Path, str], overwrite: bool = False) -> Path:
        if self.raw_bytes is None:
            raise ValueError("Raw message data is not available.")

        return self._write_text_or_bytes(
            destination, self.raw_bytes, overwrite=overwrite
        )

    def save_text(self, destination: Union[Path, str], overwrite: bool = False) -> Path:
        """Save the decoded plain-text body using UTF-8."""
        return self._write_text_or_bytes(
            destination, self.text_body, overwrite=overwrite
        )

    def save_html(self, destination: Union[Path, str], overwrite: bool = False) -> Path:
        """Save the decoded HTML body using UTF-8."""
        return self._write_text_or_bytes(
            destination, self.html_body, overwrite=overwrite
        )

    def save_attachments(
        self, destination: Union[Path, str], overwrite: bool = False
    ) -> list[Path]:
        """Save all attachments into a directory and return their paths."""
        directory = Path(destination).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)

        paths = [directory / attachment.filename for attachment in self.attachments]
        if len(paths) != len(set(paths)):
            raise FileExistsError("Message contains duplicate attachment filenames.")
        if not overwrite:
            existing = next((path for path in paths if path.exists()), None)
            if existing is not None:
                raise FileExistsError(f"Attachment already exists: {existing}")

        return [
            attachment.save(path, overwrite=overwrite)
            for attachment, path in zip(self.attachments, paths)
        ]

    @staticmethod
    def _write_text_or_bytes(
        destination: Union[Path, str],
        content: Union[str, bytes],
        *,
        overwrite: bool,
    ) -> Path:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists() and not overwrite:
            raise FileExistsError(f"Message file already exists: {path}")

        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path


@dataclass(frozen=True)
class Contact:
    """A contact stored in a Thunderbird address book."""

    name: str
    email: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email}
