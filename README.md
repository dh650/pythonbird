# pythonbird

[![PyPI](https://img.shields.io/pypi/v/pythonbird)](https://pypi.org/project/pythonbird/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pythonbird)](https://pypi.org/project/pythonbird/)
[![License](https://img.shields.io/github/license/rchbld/pythonbird)](LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pythonbird)](https://pypi.org/project/pythonbird/)

A lightweight, zero-dependency Python library for reading local Mozilla Thunderbird profiles, mailboxes, address books, and opening native compose windows on Linux.

Current version: **0.3.0**

## Features

- Detects standard, Snap, and Flatpak Thunderbird profiles.
- Supports explicitly selected or backed-up profile directories.
- Reads configured accounts from `prefs.js`.
- Discovers local and IMAP Mbox folders, including nested `.sbd` folders.
- Returns typed `Message`, `Attachment`, and `Contact` objects.
- Searches by addresses, subject, content, dates, attachments, flags, and tags.
- Reads Thunderbird read, starred, replied, and forwarded status metadata.
- Reads Thunderbird tags from `X-Mozilla-Keys`.
- Saves attachments, EML files, decoded text bodies, and HTML bodies.
- Exports folders to JSON.
- Reads SQLite address books in read-only mode.
- Opens Thunderbird compose windows without using a system shell.
- Preserves the dictionary-based API from pythonbird 0.1.x.

## Requirements

- Linux
- Python 3.9 or newer
- Mozilla Thunderbird only when opening compose windows

Reading an explicitly supplied profile or backup does not require Thunderbird to be installed.

## Installation

```bash
pip install pythonbird
```

or:

```bash
poetry add pythonbird
```

## Quick start

```python
from pythonbird import Thunderbird, __version__

print(__version__)

tb = Thunderbird()

print(tb.profile_dir)
print(tb.accounts())
print(tb.folders())

for message in tb.messages("Inbox", limit=20):
    print(message.subject, message.sender, message.read)
```

Use an explicit profile when automatic detection is not appropriate:

```python
tb = Thunderbird(
    profile_dir="/home/user/.thunderbird/example.default-release",
    command=["thunderbird"],
)
```

## Folders

Canonical folder names use `/` for nesting:

```python
for folder in tb.folders():
    print(folder)

messages = tb.messages("Archive/2026")
```

A unique short folder name is accepted. When several folders have the same short name, use the full name returned by `folders()`.

## Searching messages

```python
from datetime import date

results = tb.search(
    "Inbox",
    sender="github.com",
    recipient="example.com",
    subject="report",
    contains="release",
    after=date(2026, 1, 1),
    before=date(2026, 12, 31),
    has_attachments=True,
    unread=True,
    starred=True,
    replied=False,
    forwarded=False,
    tags=["work", "important"],
    limit=50,
)
```

For large mailboxes, use the iterator:

```python
for message in tb.iter_search("Inbox", unread=True):
    print(message.subject)
```

Tag matching is case-insensitive and all requested tags must be present. Messages without a valid Thunderbird status do not match `unread=True` or `unread=False`.

## Message metadata

```python
message = tb.messages("Inbox", limit=1)[0]

print(message.sender)
print(message.recipients)
print(message.subject)
print(message.date)
print(message.text_body)
print(message.html_body)
print(message.read)       # True, False, or None when status is unavailable
print(message.starred)
print(message.replied)
print(message.forwarded)
print(message.tags)
```

Status and tag support is read-only. Version 0.3.0 does not modify Mbox files or Thunderbird indexes.

## Attachments and export

```python
message.save_attachments("downloads")
message.save_eml("exports/message.eml")
message.save_text("exports/message.txt")
message.save_html("exports/message.html")

tb.export_json("exports/inbox.json", folder="Inbox", limit=100)
```

Existing files are not overwritten unless `overwrite=True` is explicitly passed to a model save method.

## Contacts

```python
for contact in tb.contacts():
    print(contact.name, contact.email)
```

Read a different Thunderbird address book:

```python
contacts = tb.contacts(
    database_path="/path/to/address-book.sqlite",
    strict=True,
)
```

With `strict=False`, SQLite and schema errors produce an empty list instead of raising `ThunderbirdContactsError`.

## Compose window

```python
tb.compose(
    to="developer@example.com",
    subject="Created with pythonbird",
    body="Hello from pythonbird!",
    attachment_path="/path/to/report.pdf",
)
```

The compose window is opened through an argument list without `shell=True`. The attachment must exist.

## Low-level and legacy APIs

The public low-level classes remain available:

```python
from pythonbird import ThunderbirdContacts, ThunderbirdLinux, ThunderbirdMail

client = ThunderbirdLinux()
mail = ThunderbirdMail(client)
contacts = ThunderbirdContacts(client)
```

The 0.1.x dictionary API is preserved:

```python
messages = mail.get_local_inbox_messages(limit=20)

for message in mail.iter_mbox_messages("/path/to/mbox"):
    print(message["subject"])
```

## Safety and limitations

- pythonbird 0.3.0 reads mail and address-book data but does not change Mbox files.
- Thunderbird metadata headers may be absent or stale; `read` is therefore optional.
- IMAP folders must be present in the local Thunderbird profile to be readable.
- Calendar, SMTP sending, watchers, and Windows/macOS profile support are not included.
- Work with a backup when inspecting important profiles from custom scripts.

See [GUIDE.md](GUIDE.md) for the complete API reference and [CHANGELOG.md](CHANGELOG.md) for release history.

## Development

```bash
poetry install
poetry run pytest
poetry run black --check .
poetry run flake8 pythonbird tests
poetry build
```

## License

MIT. See [LICENSE](LICENSE).
