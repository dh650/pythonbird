# pythonbird

[![PyPI](https://img.shields.io/pypi/v/pythonbird)](https://pypi.org/project/pythonbird/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pythonbird)](https://pypi.org/project/pythonbird/)
[![License](https://img.shields.io/github/license/rchbld/pythonbird)](LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pythonbird)](https://pypi.org/project/pythonbird/)

A lightweight, zero-dependency Python library for interacting with local Mozilla Thunderbird profiles, mailboxes, address books, and native compose windows on Linux.

## Features

- **Profile Auto-Detection:** Detects standard, Snap, and Flatpak Thunderbird profile directories.
- **Manual Profile Selection:** Allows applications to work with a specific profile or a backed-up profile directory.
- **Preference Parsing:** Reads configured email accounts and supported values from `prefs.js`.
- **Local Mail Reader:** Reads messages from Thunderbird Mbox files.
- **Folder Discovery:** Lists and resolves local and account mail folders.
- **Message Search:** Filters by sender, recipient, subject, content, date, and attachments.
- **Typed Models:** Returns `Message`, `Attachment`, and `Contact` objects.
- **Attachment Extraction:** Inspects and saves files attached to messages.
- **Export:** Saves messages as EML or exports folders to JSON.
- **High-Level API:** Groups profile, mail, contacts, search, compose, and export operations in `Thunderbird`.
- **Memory-Efficient Iteration:** Supports reading large mailboxes without loading every message into memory.
- **MIME Decoding:** Decodes encoded headers, declared character sets, plain-text bodies, and HTML bodies.
- **Address Book Access:** Reads contacts from Thunderbird SQLite address books in read-only mode.
- **Native Compose Window:** Opens a Thunderbird compose window with a recipient, subject, body, and optional attachment.
- **Safe Process Launching:** Starts Thunderbird without passing message fields through a system shell.

## Documentation

See the complete [Developer Guide and API Reference](GUIDE.md).

Release history is available in [CHANGELOG.md](CHANGELOG.md).

## Requirements

- Linux
- Python 3.9 or newer
- Mozilla Thunderbird for compose-window functionality

Reading an explicitly supplied profile directory does not require Thunderbird to be installed. Opening a compose window requires an available Thunderbird command.

## Installation

### Using Poetry

```bash
poetry add pythonbird
```

### Using pip

```bash
pip install pythonbird
```

## Quick Start

The recommended API in version 0.2.0 uses one high-level object:

```python
from pythonbird import Thunderbird

tb = Thunderbird()

print(tb.accounts())
print(tb.folders())

for message in tb.messages("Inbox", limit=20):
    print(message.subject, message.sender)

results = tb.search(
    "Inbox",
    subject="report",
    has_attachments=True,
)

for attachment in results[0].attachments:
    attachment.save("downloads/")

tb.export_json("inbox.json", folder="Inbox")
```

The low-level `ThunderbirdLinux`, `ThunderbirdMail`, and
`ThunderbirdContacts` APIs from version 0.1.x remain available.


```python
from pythonbird import (
    ThunderbirdContacts,
    ThunderbirdLinux,
    ThunderbirdMail,
)

# Automatically detect the active Thunderbird profile.
tb = ThunderbirdLinux()

print(f"Active profile: {tb.profile_dir}")
print(f"Configured accounts: {tb.get_mail_accounts()}")

# Read up to 100 messages from the local Inbox.
mail_manager = ThunderbirdMail(tb)
messages = mail_manager.get_local_inbox_messages(limit=100)

for message in messages:
    print(f"From: {message['from']}")
    print(f"Subject: {message['subject']}")
    print(f"Body: {message['body'][:100]}")
    print()

# Read contacts from abook.sqlite.
contact_manager = ThunderbirdContacts(tb)
contacts = contact_manager.get_all_contacts()

for contact in contacts:
    print(f"{contact['name']}: {contact['email']}")

# Open a native Thunderbird compose window.
tb.open_compose_window(
    to="developer@example.com",
    subject="Draft created with pythonbird",
    body="Hello from pythonbird!",
)
```

## Using a Specific Profile

Automatic profile detection is used by default:

```python
tb = ThunderbirdLinux()
```

A profile can also be supplied explicitly:

```python
tb = ThunderbirdLinux(
    profile_dir="/home/user/.thunderbird/example.default-release",
)
```

This is useful when:

- multiple profiles exist;
- Thunderbird uses a custom profile location;
- a backed-up profile needs to be inspected;
- tests should not use the real user profile.

The launch command can also be supplied explicitly:

```python
tb = ThunderbirdLinux(
    profile_dir="/path/to/profile",
    command=["flatpak", "run", "org.mozilla.Thunderbird"],
)
```

## Reading Mail

### Read the Local Inbox

```python
mail_manager = ThunderbirdMail(tb)

messages = mail_manager.get_local_inbox_messages(limit=50)
```

Each message is returned as a dictionary:

```python
{
    "id": 0,
    "from": "Sender <sender@example.com>",
    "to": "Recipient <recipient@example.com>",
    "subject": "Message subject",
    "date": "Fri, 10 Jul 2026 12:00:00 +0300",
    "body": "Preferred plain-text body",
    "text_body": "Plain-text body",
    "html_body": "<p>HTML body</p>",
}
```

### Iterate Over a Large Inbox

```python
for message in mail_manager.iter_local_inbox_messages():
    print(message["subject"])
```

This avoids creating a list containing every message in memory.

### Read Another Mbox File

```python
messages = mail_manager.get_mbox_messages(
    "/home/user/.thunderbird/profile/Mail/Local Folders/Sent",
    limit=100,
)
```

An arbitrary Mbox file can also be iterated:

```python
for message in mail_manager.iter_mbox_messages(
    "/path/to/mailbox",
):
    print(message["subject"])
```

## Reading Contacts

```python
contact_manager = ThunderbirdContacts(tb)
contacts = contact_manager.get_all_contacts()
```

By default, contacts are read from:

```text
<profile>/abook.sqlite
```

A different database can be supplied:

```python
contacts = contact_manager.get_all_contacts(
    database_path="/path/to/address-book.sqlite",
)
```

Database and schema errors raise `ThunderbirdContactsError` by default.

To return an empty list instead:

```python
contacts = contact_manager.get_all_contacts(strict=False)
```

## Opening a Compose Window

```python
tb.open_compose_window(
    to="friend@example.com",
    subject="Report",
    body="The report is attached.",
    attachment_path="/home/user/Documents/report.pdf",
)
```

The attachment must exist. Otherwise, `FileNotFoundError` is raised.

Thunderbird is launched without `shell=True`.

## Error Handling

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
    print(f"Required profile, executable, or file was not found: {error}")

except PermissionError as error:
    print(f"Access was denied: {error}")

except ThunderbirdContactsError as error:
    print(f"Address book could not be read: {error}")
```

## Running Tests

If Poetry dependencies are already installed:

```bash
poetry run python -m pytest -v
```

If the Poetry environment is already activated:

```bash
python -m pytest -v
```

The tests use temporary mock profiles and do not read the user's real Thunderbird profile.

## Development Checks

Format the code:

```bash
poetry run black .
```

Run linting:

```bash
poetry run flake8 pythonbird tests
```

Run tests:

```bash
poetry run python -m pytest -v
```

Build the package:

```bash
poetry build
```

## Project Structure

```text
pythonbird/
├── pythonbird/
│   ├── __init__.py
│   ├── core.py
│   ├── mail.py
│   └── contacts.py
├── tests/
│   ├── test_core.py
│   ├── test_compose.py
│   ├── test_contacts.py
│   └── test_mail_encoding.py
├── CHANGELOG.md
├── GUIDE.md
├── LICENSE
├── README.md
├── poetry.lock
└── pyproject.toml
```

## Safety

Pythonbird is designed to avoid modifying Thunderbird profile data:

- SQLite address books are opened in read-only mode;
- mailbox messages are read without intentionally modifying their contents;
- Thunderbird is launched without `shell=True`;
- attachment paths are validated before opening the compose window.

Applications should still keep backups of important Thunderbird profiles. No library can guarantee zero risk when files may be changed concurrently by another process.

## Version

Current version: **0.2.0**

## License

This project is licensed under the [MIT License](LICENSE).
