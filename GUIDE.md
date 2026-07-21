# pythonbird 0.3.0 Developer Guide

This guide describes the public API of pythonbird 0.3.0. New applications should normally use the high-level `Thunderbird` facade. The low-level and legacy APIs remain available for compatibility.

## 1. Public exports

```python
from pythonbird import (
    __version__,
    Attachment,
    Contact,
    Message,
    Thunderbird,
    ThunderbirdContacts,
    ThunderbirdContactsError,
    ThunderbirdLinux,
    ThunderbirdMail,
)
```

When the installed package metadata is available, `__version__` is read from it. A source checkout that has not been installed returns `0.3.0.dev0`.

## 2. High-level API

### Creating a client

```python
from pythonbird import Thunderbird

tb = Thunderbird()
```

Constructor:

```python
Thunderbird(profile_dir=None, command=None)
```

- `profile_dir`: explicit Thunderbird profile directory. Automatic Linux detection is used when omitted.
- `command`: launch command sequence, such as `["thunderbird"]` or `["flatpak", "run", "org.mozilla.Thunderbird"]`.

An invalid explicit profile raises `FileNotFoundError`. A command is only required for compose-window functionality, but automatic command detection occurs during construction unless a command is supplied.

### Profile and accounts

```python
profile = tb.profile_dir
accounts = tb.accounts()
```

`accounts()` returns unique configured email addresses in preference order.

### Folders

```python
folders = tb.folders()
```

The result is a case-insensitively sorted list of canonical folder names. Nested Thunderbird `.sbd` paths are represented using `/`, for example:

```text
Inbox
Archive/2026
imap.example.com/Projects/Active
```

Local Folders omit the `Local Folders` storage component. Account directories remain in canonical names so that similarly named account folders stay distinguishable.

### Reading messages

```python
messages = tb.messages(folder="Inbox", limit=100)
```

- `folder`: canonical name, unique short name, or explicit Mbox path.
- `limit`: `None` for no limit, `0` for an empty result, or a positive integer.

A negative limit raises `ValueError`. An unknown folder raises `FileNotFoundError`. An ambiguous short folder name raises `ValueError`; use the full name returned by `folders()`.

### Searching

```python
results = tb.search(
    folder="Inbox",
    sender=None,
    recipient=None,
    subject=None,
    contains=None,
    after=None,
    before=None,
    has_attachments=None,
    unread=None,
    starred=None,
    replied=None,
    forwarded=None,
    tags=None,
    limit=None,
)
```

Text filters are case-insensitive substring matches. `contains` checks the subject, plain-text body, and HTML body.

`after` and `before` accept `datetime.date` or `datetime.datetime` and are inclusive. A message with an absent or invalid date does not match a date-filtered search.

Boolean filters accept `True`, `False`, or `None` to disable the filter. `unread` is derived from the optional `Message.read` value. A message whose status is unavailable matches neither `unread=True` nor `unread=False`.

`tags` accepts a sequence. Matching is case-insensitive and requires every requested tag.

### Iterative search

```python
for message in tb.iter_search("Inbox", unread=True, limit=100):
    print(message.subject)
```

`iter_search()` accepts the same filters as `search()` but returns a lazy iterator.

### Contacts

```python
contacts = tb.contacts(database_path=None, strict=True)
```

The default database is `<profile>/abook.sqlite`. Missing database files return an empty list. SQLite or unsupported-schema errors raise `ThunderbirdContactsError` when `strict=True` and return an empty list when `strict=False`.

### JSON export

```python
path = tb.export_json(
    destination="exports/inbox.json",
    folder="Inbox",
    limit=100,
)
```

The destination parent directory is created automatically. Attachment data is not embedded; exported attachment entries contain filename, MIME type, and size.

### Compose

```python
tb.compose(
    to="user@example.com",
    subject="Subject",
    body="Body",
    attachment_path=None,
)
```

Returns the `subprocess.Popen` object. The command is launched without a shell. A supplied attachment must be an existing file.

## 3. Message model

```python
@dataclass(frozen=True)
class Message:
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
```

`body` prefers `text_body` and falls back to `html_body`.

Thunderbird metadata is read from `X-Mozilla-Status` and `X-Mozilla-Keys`. `read=None` means no valid status header was available. The other flags safely default to `False` and tags to an empty tuple.

### Saving a message

```python
message.save_eml("message.eml", overwrite=False)
message.save_text("message.txt", overwrite=False)
message.save_html("message.html", overwrite=False)
message.save_attachments("downloads", overwrite=False)
```

All methods return resolved `Path` objects; `save_attachments()` returns `list[Path]`. Parent directories are created. Existing files raise `FileExistsError` unless overwriting is explicitly enabled.

`save_eml()` raises `ValueError` when raw message bytes are unavailable, such as for a manually constructed `Message` without `raw_bytes`.

Duplicate attachment filenames are rejected before writing to avoid partial, accidental overwrites.

### Dictionary conversion

```python
item = message.to_dict()
```

The result preserves the established `from`, `to`, and body keys and adds flags and tags. Attachment objects remain objects in this conversion; `export_json()` converts them to JSON-safe metadata.

## 4. Attachment model

```python
@dataclass(frozen=True)
class Attachment:
    filename: str
    content_type: str
    data: bytes
```

`size` returns the byte length.

```python
path = attachment.save("downloads", overwrite=False)
```

A directory destination uses the attachment filename. An existing file raises `FileExistsError` unless overwriting is enabled.

## 5. Contact model

```python
@dataclass(frozen=True)
class Contact:
    name: str
    email: str
```

`to_dict()` returns `{"name": ..., "email": ...}`.

## 6. Low-level API

### ThunderbirdLinux

```python
client = ThunderbirdLinux(profile_dir=None, command=None)
```

Public attributes and methods:

- `profile_dir`: active profile path.
- `base_dir`: profile root or explicit profile parent.
- `prefs`: parsed `prefs.js` values.
- `cmd`: command argument list.
- `get_mail_accounts()`.
- `open_compose_window(...)`.

Automatic profile roots:

```text
~/.thunderbird
~/snap/thunderbird/common/.thunderbird
~/.var/app/org.mozilla.Thunderbird/.thunderbird
```

### ThunderbirdMail

```python
mail = ThunderbirdMail(client)
```

Modern methods:

- `list_folders()`
- `resolve_folder(folder)`
- `get_messages(folder="Inbox", limit=None)`
- `iter_messages(folder="Inbox", limit=None)`
- `search_messages(folder="Inbox", **filters)`
- `iter_search_messages(folder="Inbox", **filters)`
- `export_json(destination, folder="Inbox", limit=None)`

### ThunderbirdContacts

```python
address_book = ThunderbirdContacts(client)
```

Methods:

- `get_all_contacts(database_path=None, strict=True)` returns dictionaries.
- `get_contact_models(database_path=None, strict=True)` returns `Contact` objects.

The SQLite database is opened using URI read-only mode and the expected `cards` schema is checked before reading.

## 7. Legacy 0.1.x API

These methods remain supported:

```python
mail.get_local_inbox_messages(limit=None)
mail.iter_local_inbox_messages(limit=None)
mail.get_mbox_messages(mbox_path, limit=None)
mail.iter_mbox_messages(mbox_path, limit=None)
```

They return dictionaries rather than `Message` objects. New applications should prefer the modern API.

## 8. Concurrency and safety

Version 0.3.0 is read-only for Mbox and SQLite profile data. It does not mark messages, add tags, compact folders, or update `.msf` indexes. This avoids unsafe writes while Thunderbird may be running.

Mbox metadata can be missing or stale, particularly after external synchronization or index repair. Applications should treat flags as useful local metadata rather than an authoritative remote-server state.

Use backed-up profiles for untrusted experiments and do not place secrets from message bodies in logs.

## 9. Development checks

```bash
poetry install
poetry run pytest
poetry run black --check .
poetry run flake8 pythonbird tests
poetry build
```
