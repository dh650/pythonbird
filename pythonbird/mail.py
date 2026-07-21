from __future__ import annotations

import json
import mailbox
from datetime import date, datetime
from email.header import decode_header, make_header
from email.message import Message as EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union

from .core import ThunderbirdLinux
from .models import Attachment, Message


class ThunderbirdMail:
    _IGNORED_SUFFIXES = (".msf", ".dat", ".sqlite")
    _READ_FLAG = 0x0001
    _REPLIED_FLAG = 0x0002
    _STARRED_FLAG = 0x0004
    _FORWARDED_FLAG = 0x1000

    def __init__(self, tb_instance: ThunderbirdLinux):
        self.profile_dir = tb_instance.profile_dir

    # ------------------------------------------------------------------
    # Modern object API
    # ------------------------------------------------------------------
    def list_folders(self) -> list[str]:
        """Return canonical names for available local and account folders."""
        return sorted({name for name, _ in self._iter_folder_paths()}, key=str.casefold)

    def resolve_folder(self, folder: Union[str, Path]) -> Path:
        """Resolve a canonical folder name, unique short name, or mbox path."""
        candidate = Path(folder).expanduser()
        if candidate.is_file():
            return candidate.resolve()

        folder_text = str(folder).replace("\\", "/").strip("/")
        if not folder_text:
            raise FileNotFoundError("Thunderbird mail folder name is empty.")

        folders = list(self._iter_folder_paths())
        exact = [
            path for name, path in folders if name.casefold() == folder_text.casefold()
        ]
        if exact:
            return exact[0].resolve()

        short_matches = [
            path
            for name, path in folders
            if name.rsplit("/", 1)[-1].casefold() == folder_text.casefold()
        ]
        if len(short_matches) == 1:
            return short_matches[0].resolve()
        if len(short_matches) > 1:
            raise ValueError(
                f"Thunderbird folder name is ambiguous: {folder}. "
                "Use the full folder path returned by list_folders()."
            )

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
        self._validate_limit(limit)
        yield from self.iter_mbox_message_objects(
            self.resolve_folder(folder),
            limit=limit,
        )

    def search_messages(
        self,
        folder: Union[str, Path] = "Inbox",
        **filters,
    ) -> list[Message]:
        """Return messages matching the filters accepted by iter_search_messages."""
        return list(self.iter_search_messages(folder=folder, **filters))

    def iter_search_messages(
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
        unread: Optional[bool] = None,
        starred: Optional[bool] = None,
        replied: Optional[bool] = None,
        forwarded: Optional[bool] = None,
        tags: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Message]:
        """Iterate over messages matching case-insensitive filters."""
        self._validate_limit(limit)
        if limit == 0:
            return

        wanted_tags = {tag.casefold() for tag in tags or ()}
        matched = 0
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
            if unread is not None:
                if message.read is None or (not message.read) is not unread:
                    continue
            if starred is not None and message.starred is not starred:
                continue
            if replied is not None and message.replied is not replied:
                continue
            if forwarded is not None and message.forwarded is not forwarded:
                continue
            if wanted_tags:
                message_tags = {tag.casefold() for tag in message.tags}
                if not wanted_tags.issubset(message_tags):
                    continue

            if after is not None or before is not None:
                message_date = self._parse_date(message.date)
                if message_date is None:
                    continue
                if after is not None:
                    if message_date < self._normalise_date(after, message_date):
                        continue
                if before is not None:
                    if message_date > self._normalise_date(before, message_date):
                        continue

            yield message
            matched += 1
            if limit is not None and matched >= limit:
                break

    def export_json(
        self,
        destination: Union[str, Path],
        folder: Union[str, Path] = "Inbox",
        limit: Optional[int] = None,
    ) -> Path:
        self._validate_limit(limit)
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
        self._validate_limit(limit)
        if limit == 0:
            return

        path = Path(mbox_path).expanduser().resolve()
        if not path.is_file():
            return

        mbox = mailbox.mbox(path, create=False)
        try:
            for position, (message_id, message) in enumerate(mbox.iteritems()):
                if limit is not None and position >= limit:
                    break
                yield self._message_to_model(message_id, message)
        finally:
            mbox.close()

    def _iter_folder_paths(self) -> Iterator[tuple[str, Path]]:
        for root_name in ("Mail", "ImapMail"):
            root = self.profile_dir / root_name
            if not root.is_dir():
                continue

            for path in root.rglob("*"):
                if not self._is_mbox_file(path):
                    continue
                yield self._folder_display_name(root, path), path

    def _is_mbox_file(self, path: Path) -> bool:
        return path.is_file() and not path.name.endswith(self._IGNORED_SUFFIXES)

    @staticmethod
    def _folder_display_name(root: Path, path: Path) -> str:
        parts = list(path.relative_to(root).parts)
        if parts and parts[0] == "Local Folders":
            parts.pop(0)
        parts = [part[:-4] if part.endswith(".sbd") else part for part in parts]
        return "/".join(parts)

    def _message_to_model(self, message_id, message: EmailMessage) -> Message:
        bodies = self._get_bodies(message)
        status = self._parse_status(message.get("X-Mozilla-Status"))
        return Message(
            id=message_id,
            sender=self._decode_header(message.get("from")),
            recipients=self._decode_header(message.get("to")),
            subject=self._decode_header(message.get("subject")),
            date=self._decode_header(message.get("date")),
            text_body=bodies["text"],
            html_body=bodies["html"],
            attachments=tuple(self._get_attachments(message)),
            read=None if status is None else bool(status & self._READ_FLAG),
            starred=False if status is None else bool(status & self._STARRED_FLAG),
            replied=False if status is None else bool(status & self._REPLIED_FLAG),
            forwarded=False if status is None else bool(status & self._FORWARDED_FLAG),
            tags=self._parse_tags(message.get("X-Mozilla-Keys")),
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
    def _parse_status(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value.strip(), 16)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_tags(value: Optional[str]) -> tuple[str, ...]:
        if not value:
            return ()
        return tuple(dict.fromkeys(value.split()))

    @staticmethod
    def _validate_limit(limit: Optional[int]) -> None:
        if limit is not None and limit < 0:
            raise ValueError("limit must be greater than or equal to zero.")

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
        elif reference.tzinfo is None and result.tzinfo is not None:
            result = result.replace(tzinfo=None)
        return result
