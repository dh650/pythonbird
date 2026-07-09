from __future__ import annotations  # Добавьте эту строку первой
import mailbox
from pathlib import Path


class ThunderbirdMail:
    def __init__(self, tb_instance: ThunderbirdLinux):
        self.profile_dir = tb_instance.profile_dir

    def get_local_inbox_messages(self) -> list:
        """Reads and extracts messages from the local 'Inbox' mbox file."""
        mbox_path = self.profile_dir / "Mail" / "Local Folders" / "Inbox"

        if not mbox_path.exists():
            return []

        mbox = mailbox.mbox(mbox_path)
        messages = []

        mbox.lock()
        try:
            for msg_id, message in mbox.items():
                messages.append(
                    {
                        "id": msg_id,
                        "from": message["from"],
                        "subject": message["subject"],
                        "date": message["date"],
                        "body": self._get_body(message),
                    }
                )
        finally:
            mbox.unlock()

        return messages

    def _get_body(self, message) -> str:
        """Extracts the plain text body from an email message."""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="ignore")
        else:
            return message.get_payload(decode=True).decode(errors="ignore")
        return ""
