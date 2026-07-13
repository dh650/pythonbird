from __future__ import annotations

import json
import mailbox
from datetime import date, datetime
from email.header import decode_header, make_header
from email.message import Message as EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterator, Optional, Union

from .core import ThunderbirdLinux
from .models import Attachment, Message


class ThunderbirdMail:
    def __init__(self, tb_instance: ThunderbirdLinux):
        self.profile_dir = tb_instance.profile_dir

    # ------------------------------------------------------------------
    # Modern object API
    # ------------------------------------------------------------------
    def list_folders(self) -> list[str]:
        """Return available local and account mail folders."""
        folders: set[str] = set()

        for root_name in ("Mail", "ImapMail"):
            root = self.profile_dir / root_name
            if not root.is_dir():
                continue

            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name.endswith((".msf", ".dat", ".sqlite")):
                    continue
                if ".sbd" in file_path.parts:
                    display_parts = []
                    for part in file_path.relative_to(root).parts:
                        display_parts.append(
                            part[:-4] if part.endswith(".sbd") else part
                        )
                    folders.add("/".join(display_parts))
                elif file_path.parent.name.endswith(".sbd"):
                    folders.add(file_path.stem)
                else:
                    relative = file_path.relative_to(root)
                    if relative.parts and relative.parts[0] == "Local Folders":
                        relative = Path(*relative.parts[1:])
                    folders.add(str(relative))

        return sorted(folders, key=str.casefold)

    def resolve_folder(self, folder: Union[str, Path]) -> Path:
        """Resolve a Thunderbird folder name or explicit mbox path."""
        candidate = Path(folder).expanduser()
        if candidate.is_file():
            return candidate.resolve()

        folder_text = str(folder).replace("\\", "/").strip("/")
        direct_candidates = [
            self.profile_dir / "Mail" / "Local Folders" / folder_text,
            self.profile_dir / "Mail" / folder_text,
            self.profile_dir / "ImapMail" / folder_text,
        ]
        for path in direct_candidates:
            if path.is_file():
                return path.resolve()

        wanted = folder_text.casefold()
        for root_name in ("Mail", "ImapMail"):
            root = self.profile_dir / root_name
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.name.endswith(".msf"):
                    continue
                relative = str(path.relative_to(root)).replace(".sbd/", "/")
                if relative.casefold() == wanted or path.name.casefold() == wanted:
                    return path.resolve()

        raise FileNotFoundError(f"Thunderbird mail folder was not found: {folder}")

    def get_messages(
        self,
        folder: Union[str, Path] = "Inbox",
        limit: Optional[int] = None,
    ) -> list[Message]:
        return list(self.iter_messages(folder=folder, limit=limit))

    def iter_messages(
        self,
        folder: Union[str, Path] = "Inbox",
        limit: Optional[int] = None,
    ) -> Iterator[Message]:
        yield from self.iter_mbox_message_objects(
            self.resolve_folder(folder),
            limit=limit,
        )

    def search_messages(
        self,
        folder: Union[str, Path] = "Inbox",
        *,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        contains: Optional[str] = None,
        after: Optional[Union[date, datetime]] = None,
        before: Optional[Union[date, datetime]] = None,
        has_attachments: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> list[Message]:
        """Search messages using case-insensitive filters."""
        results: list[Message] = []
        for message in self.iter_messages(folder):
            if sender and sender.casefold() not in message.sender.casefold():
                continue
            if recipient and recipient.casefold() not in message.recipients.casefold():
                continue
            if subject and subject.casefold() not in message.subject.casefold():
                continue
            if contains:
                haystack = (
                    f"{message.subject}\n{message.text_body}\n{message.html_body}"
                )
                if contains.casefold() not in haystack.casefold():
                    continue
            if has_attachments is not None:
                if bool(message.attachments) is not has_attachments:
                    continue

            message_date = self._parse_date(message.date)
            if after is not None and message_date is not None:
                if message_date < self._normalise_date(after, message_date):
                    continue
            if before is not None and message_date is not None:
                if message_date > self._normalise_date(before, message_date):
                    continue

            results.append(message)
            if limit is not None and len(results) >= limit:
                break

        return results

    def export_json(
        self,
        destination: Union[str, Path],
        folder: Union[str, Path] = "Inbox",
        limit: Optional[int] = None,
    ) -> Path:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for message in self.iter_messages(folder, limit=limit):
            item = message.to_dict()
            item["attachments"] = [
                {
                    "filename": attachment.filename,
                    "content_type": attachment.content_type,
                    "size": attachment.size,
                }
                for attachment in message.attachments
            ]
            payload.append(item)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    # ------------------------------------------------------------------
    # Backward-compatible v0.1.x dictionary API
    # ------------------------------------------------------------------
    def get_local_inbox_messages(self, limit: Optional[int] = None) -> list[dict]:
        return list(self.iter_local_inbox_messages(limit=limit))

    def iter_local_inbox_messages(self, limit: Optional[int] = None) -> Iterator[dict]:
        for message in self.iter_messages("Inbox", limit=limit):
            yield message.to_dict()

    def get_mbox_messages(
        self, mbox_path: Union[str, Path], limit: Optional[int] = None
    ) -> list[dict]:
        return list(self.iter_mbox_messages(mbox_path=mbox_path, limit=limit))

    def iter_mbox_messages(
        self, mbox_path: Union[str, Path], limit: Optional[int] = None
    ) -> Iterator[dict]:
        for message in self.iter_mbox_message_objects(mbox_path, limit=limit):
            yield message.to_dict()

    def iter_mbox_message_objects(
        self, mbox_path: Union[str, Path], limit: Optional[int] = None
    ) -> Iterator[Message]:
        path = Path(mbox_path).expanduser().resolve()
        if not path.is_file():
            return
        if limit is not None and limit < 0:
            raise ValueError("limit must be greater than or equal to zero.")

        mbox = mailbox.mbox(path, create=False)
        try:
            for position, (message_id, message) in enumerate(mbox.iteritems()):
                if limit is not None and position >= limit:
                    break
                yield self._message_to_model(message_id, message)
        finally:
            mbox.close()

    def _message_to_model(self, message_id, message: EmailMessage) -> Message:
        bodies = self._get_bodies(message)
        return Message(
            id=message_id,
            sender=self._decode_header(message.get("from")),
            recipients=self._decode_header(message.get("to")),
            subject=self._decode_header(message.get("subject")),
            date=self._decode_header(message.get("date")),
            text_body=bodies["text"],
            html_body=bodies["html"],
            attachments=tuple(self._get_attachments(message)),
            raw_bytes=message.as_bytes(),
        )

    def _get_bodies(self, message: EmailMessage) -> dict[str, str]:
        text_parts: list[str] = []
        html_parts: list[str] = []
        parts = message.walk() if message.is_multipart() else [message]
        for part in parts:
            if part.is_multipart() or part.get_content_disposition() == "attachment":
                continue
            decoded = self._decode_part(part)
            if not decoded:
                continue
            if part.get_content_type() == "text/plain":
                text_parts.append(decoded)
            elif part.get_content_type() == "text/html":
                html_parts.append(decoded)
        return {
            "text": "\n".join(text_parts).strip(),
            "html": "\n".join(html_parts).strip(),
        }

    def _get_attachments(self, message: EmailMessage) -> Iterator[Attachment]:
        for part in message.walk():
            filename = part.get_filename()
            disposition = part.get_content_disposition()
            if disposition != "attachment" and not filename:
                continue
            payload = part.get_payload(decode=True) or b""
            yield Attachment(
                filename=self._decode_header(filename) or "attachment",
                content_type=part.get_content_type(),
                data=payload,
            )

    @staticmethod
    def _decode_part(part: EmailMessage) -> str:
        payload = part.get_payload(decode=True)
        if payload is None:
            raw_payload = part.get_payload()
            return raw_payload if isinstance(raw_payload, str) else ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset)
        except (LookupError, UnicodeDecodeError):
            return payload.decode("utf-8", errors="replace")

    @staticmethod
    def _decode_header(value: Optional[str]) -> str:
        if value is None:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except (LookupError, UnicodeDecodeError):
            return value

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _normalise_date(value: Union[date, datetime], reference: datetime) -> datetime:
        if isinstance(value, datetime):
            result = value
        else:
            result = datetime.combine(value, datetime.min.time())
        if reference.tzinfo is not None and result.tzinfo is None:
            result = result.replace(tzinfo=reference.tzinfo)
        return result
