# Pythonbird Developer Guide and API Reference

This guide describes the public classes, methods, return values, and error-handling behavior available in `pythonbird` version **0.2.0**.

## Table of Contents

1. [Architecture](#1-architecture)
2. [ThunderbirdLinux](#2-thunderbirdlinux)
3. [ThunderbirdMail](#3-thunderbirdmail)
4. [ThunderbirdContacts](#4-thunderbirdcontacts)
5. [Error Handling](#5-error-handling)
6. [Safety and Concurrent Access](#6-safety-and-concurrent-access)


# 0. Recommended High-Level API

Version 0.2.0 adds the `Thunderbird` facade while preserving the 0.1.x API.

```python
from pythonbird import Thunderbird

tb = Thunderbird(profile_dir="/path/to/profile", command=["thunderbird"])

folders = tb.folders()
messages = tb.messages("Inbox", limit=100)
contacts = tb.contacts()
results = tb.search(subject="invoice", has_attachments=True)
tb.export_json("inbox.json")
```

Messages, contacts, and attachments are represented by typed dataclasses:

```python
message.subject
message.sender
message.text_body
message.html_body
message.attachments

attachment.filename
attachment.content_type
attachment.size
attachment.save("downloads/")

contact.name
contact.email
```

A message can be saved in EML format:

```python
message.save_eml("message.eml")
```

Search supports `sender`, `recipient`, `subject`, `contains`, `after`,
`before`, `has_attachments`, and `limit`.

# 1. Architecture

Pythonbird provides three main components:

- `ThunderbirdLinux` detects profiles, parses preferences, and opens Thunderbird compose windows.
- `ThunderbirdMail` reads messages from Thunderbird Mbox files.
- `ThunderbirdContacts` reads contacts from Thunderbird SQLite address books.

The library does not require third-party runtime dependencies.

```python
from pythonbird import (
    ThunderbirdContacts,
    ThunderbirdLinux,
    ThunderbirdMail,
)
```

# 2. ThunderbirdLinux

## Constructor

```python
ThunderbirdLinux(
    profile_dir=None,
    command=None,
)
```

## Parameters

### `profile_dir`

Optional path to a Thunderbird profile.

Accepted values:

- `str`;
- `pathlib.Path`;
- `None`.

When omitted, Pythonbird detects the profile automatically.

```python
tb = ThunderbirdLinux(
    profile_dir="/home/user/.thunderbird/example.default-release",
)
```

If the directory does not exist, `FileNotFoundError` is raised.

### `command`

Optional sequence containing the command used to launch Thunderbird.

Regular installation:

```python
tb = ThunderbirdLinux(
    profile_dir="/path/to/profile",
    command=["thunderbird"],
)
```

Flatpak installation:

```python
tb = ThunderbirdLinux(
    profile_dir="/path/to/profile",
    command=["flatpak", "run", "org.mozilla.Thunderbird"],
)
```

When omitted, Pythonbird detects a regular Thunderbird installation or a Flatpak installation.

## Profile Detection

Pythonbird checks these profile roots:

```text
~/.thunderbird
~/snap/thunderbird/common/.thunderbird
~/.var/app/org.mozilla.Thunderbird/.thunderbird
```

It then reads `profiles.ini`.

The profile is selected in this order:

1. `Default` value from an `Install*` section;
2. a `Profile*` section containing `Default=1`;
3. a directory ending in `.default-release` or `.default`.

A missing profile root, `profiles.ini`, or selected profile raises `FileNotFoundError`.

## Properties

### `base_dir`

```python
tb.base_dir
```

A `pathlib.Path` containing the Thunderbird profile root.

### `profile_dir`

```python
tb.profile_dir
```

A resolved `pathlib.Path` containing the selected Thunderbird profile.

### `prefs`

```python
tb.prefs
```

A dictionary containing supported values parsed from `prefs.js`.

Supported values include:

- strings;
- integers;
- floating-point values;
- booleans;
- `None`;
- unrecognized raw values.

### `cmd`

```python
tb.cmd
```

A list containing the process command.

Examples:

```python
["thunderbird"]
```

or:

```python
["flatpak", "run", "org.mozilla.Thunderbird"]
```

## `get_mail_accounts`

```python
get_mail_accounts() -> list[str]
```

Returns email addresses found in preferences matching:

```text
mail.identity.*.useremail
```

Duplicate values are removed while preserving their order.

```python
for account in tb.get_mail_accounts():
    print(account)
```

## `open_compose_window`

```python
open_compose_window(
    to,
    subject,
    body,
    attachment_path=None,
) -> subprocess.Popen
```

Opens a native Thunderbird compose window.

Parameters:

- `to`: recipient address;
- `subject`: message subject;
- `body`: plain-text message body;
- `attachment_path`: optional attachment path.

```python
process = tb.open_compose_window(
    to="friend@example.com",
    subject="Pythonbird test",
    body="This draft was created from Python.",
    attachment_path="/home/user/Documents/report.pdf",
)
```

The method returns the `subprocess.Popen` instance.

If the attachment does not exist, `FileNotFoundError` is raised.

Pythonbird passes process arguments directly as a list and does not use `shell=True`.

# 3. ThunderbirdMail

## Constructor

```python
ThunderbirdMail(tb_instance)
```

```python
mail_manager = ThunderbirdMail(tb)
```

## Message Format

Messages are returned as dictionaries:

```python
{
    "id": 0,
    "from": "Sender <sender@example.com>",
    "to": "Recipient <recipient@example.com>",
    "subject": "Example subject",
    "date": "Fri, 10 Jul 2026 12:00:00 +0300",
    "body": "Plain-text body",
    "text_body": "Plain-text body",
    "html_body": "<p>HTML body</p>",
}
```

Fields:

- `id`: message identifier from the Mbox reader;
- `from`: decoded sender header;
- `to`: decoded recipient header;
- `subject`: decoded subject header;
- `date`: decoded date header;
- `body`: plain-text body retained for compatibility;
- `text_body`: decoded plain-text body;
- `html_body`: decoded HTML body.

MIME-encoded headers are decoded automatically.

Message parts use their declared character set where possible. If decoding fails, Pythonbird falls back to UTF-8 with replacement characters.

Text and HTML attachments are not treated as the message body.

## `get_local_inbox_messages`

```python
get_local_inbox_messages(
    limit=None,
) -> list[dict]
```

Reads messages from:

```text
<profile>/Mail/Local Folders/Inbox
```

```python
messages = mail_manager.get_local_inbox_messages(limit=100)
```

If the Inbox file does not exist, an empty list is returned.

## `iter_local_inbox_messages`

```python
iter_local_inbox_messages(
    limit=None,
) -> Iterator[dict]
```

Iterates over Inbox messages without creating a list containing the entire mailbox.

```python
for message in mail_manager.iter_local_inbox_messages():
    print(message["subject"])
```

This method is recommended for large mailboxes.

## `get_mbox_messages`

```python
get_mbox_messages(
    mbox_path,
    limit=None,
) -> list[dict]
```

Reads an arbitrary Mbox file.

```python
messages = mail_manager.get_mbox_messages(
    "/home/user/.thunderbird/profile/Mail/Local Folders/Sent",
    limit=50,
)
```

## `iter_mbox_messages`

```python
iter_mbox_messages(
    mbox_path,
    limit=None,
) -> Iterator[dict]
```

Iterates over an arbitrary Mbox file.

If `limit` is negative, `ValueError` is raised.

If the file does not exist, the iterator returns no messages.

# 4. ThunderbirdContacts

## Constructor

```python
ThunderbirdContacts(tb_instance)
```

```python
contact_manager = ThunderbirdContacts(tb)
```

## `get_all_contacts`

```python
get_all_contacts(
    database_path=None,
    strict=True,
) -> list[dict]
```

Reads contacts from a Thunderbird SQLite address book.

### `database_path`

Optional explicit path to an SQLite address book.

When omitted, Pythonbird reads:

```text
<profile>/abook.sqlite
```

### `strict`

Controls database error behavior.

When `True`, unsupported schemas and SQLite errors raise an exception.

When `False`, these errors return an empty list.

Return value:

```python
[
    {
        "name": "Test User",
        "email": "test@example.com",
    }
]
```

Contacts without a primary email address are skipped.

Results are ordered by display name.

```python
contacts = contact_manager.get_all_contacts()

for contact in contacts:
    print(contact["name"], contact["email"])
```

Read another address book:

```python
contacts = contact_manager.get_all_contacts(
    database_path="/path/to/history.sqlite",
)
```

Use non-strict mode:

```python
contacts = contact_manager.get_all_contacts(
    strict=False,
)
```

## `ThunderbirdContactsError`

```python
from pythonbird import ThunderbirdContactsError
```

Raised when an address book exists but cannot be read using the expected schema.

Possible causes:

- corrupted SQLite database;
- missing `cards` table;
- missing required columns;
- unsupported Thunderbird database schema.

# 5. Error Handling

```python
from pythonbird import (
    ThunderbirdContacts,
    ThunderbirdContactsError,
    ThunderbirdLinux,
)

try:
    tb = ThunderbirdLinux()
    contacts = ThunderbirdContacts(tb).get_all_contacts()

except FileNotFoundError as error:
    print(f"Required file, profile, executable, or attachment is missing: {error}")

except PermissionError as error:
    print(f"Access was denied: {error}")

except ThunderbirdContactsError as error:
    print(f"Address book error: {error}")

except ValueError as error:
    print(f"Invalid argument: {error}")
```

## Common Errors

### Thunderbird profile directory was not found

Possible causes:

- Thunderbird has not been launched by the current user;
- the profile uses a custom path;
- the installation type is not supported by automatic detection.

Supply the profile explicitly:

```python
tb = ThunderbirdLinux(
    profile_dir="/custom/profile/path",
)
```

### Thunderbird executable was not found

This only affects functionality that launches Thunderbird.

Supply the command explicitly:

```python
tb = ThunderbirdLinux(
    profile_dir="/path/to/profile",
    command=["thunderbird"],
)
```

### Empty accounts list

No supported `mail.identity.*.useremail` values were found in `prefs.js`.

### Empty message list

Possible causes:

- the selected Mbox file does not exist;
- the mailbox is empty;
- a different account or storage folder is being used.

### Empty contacts list

Possible causes:

- `abook.sqlite` does not exist;
- no contacts contain a primary email address;
- `strict=False` suppressed an address book error.

# 6. Safety and Concurrent Access

Pythonbird avoids intentional writes to Thunderbird profile data.

## SQLite Address Books

SQLite address books are opened using:

```text
mode=ro
```

This prevents Pythonbird from modifying the database.

## Mbox Files

Mbox files are opened for reading and closed after iteration finishes.

Pythonbird does not intentionally edit or rewrite mailbox files. Another process may still update the same mailbox while it is being read.

Applications requiring a stable snapshot should copy the mailbox before processing it.

## Process Launching

Thunderbird is started with a list of command arguments:

```python
subprocess.Popen(
    ["thunderbird", "-compose", compose_arguments],
)
```

Pythonbird does not use:

```python
shell=True
```

This prevents message fields from being interpreted as shell commands.

## Backups

Read-only behavior reduces risk but cannot provide an absolute guarantee against all filesystem or concurrent-access problems.

Keep backups of important Thunderbird profiles.

# License

This project is licensed under the [MIT License](LICENSE).
