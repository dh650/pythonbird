from datetime import date
from email.message import EmailMessage

import pytest

import pythonbird
from pythonbird import Message, Thunderbird


def write_mbox(path, messages):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b""
    for index, message in enumerate(messages):
        content += (
            f"From sender{index}@example.com Fri Jul 10 12:00:00 2026\n".encode()
            + message.as_bytes()
            + b"\n\n"
        )
    path.write_bytes(content)


def make_message(subject, *, status=None, tags=None, message_date=True):
    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "user@example.com"
    message["Subject"] = subject
    if message_date:
        message["Date"] = "Fri, 10 Jul 2026 12:00:00 +0000"
    if status is not None:
        message["X-Mozilla-Status"] = status
    if tags is not None:
        message["X-Mozilla-Keys"] = tags
    message.set_content(f"Body for {subject}")
    return message


def make_profile(tmp_path):
    profile = tmp_path / "test.default-release"
    (profile / "prefs.js").parent.mkdir(parents=True)
    (profile / "prefs.js").write_text("", encoding="utf-8")
    return profile


def test_nested_folders_and_ambiguous_short_names(tmp_path):
    profile = make_profile(tmp_path)
    write_mbox(
        profile / "Mail" / "Local Folders" / "Archive.sbd" / "2026",
        [make_message("Archive")],
    )
    write_mbox(
        profile / "Mail" / "account.example" / "Projects.sbd" / "2026",
        [make_message("Project")],
    )

    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])

    assert tb.folders() == ["account.example/Projects/2026", "Archive/2026"]
    assert tb.messages("Archive/2026")[0].subject == "Archive"
    with pytest.raises(ValueError, match="ambiguous"):
        tb.messages("2026")


def test_flags_tags_and_iterative_search(tmp_path):
    profile = make_profile(tmp_path)
    status = format(0x0001 | 0x0002 | 0x0004 | 0x1000, "04x")
    write_mbox(
        profile / "Mail" / "Local Folders" / "Inbox",
        [
            make_message("Matched", status=status, tags="work important work"),
            make_message("Unread", status="0000", tags="personal"),
        ],
    )

    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])
    first = tb.messages()[0]
    assert first.read is True
    assert first.starred is True
    assert first.replied is True
    assert first.forwarded is True
    assert first.tags == ("work", "important")

    found = list(
        tb.iter_search(
            starred=True,
            replied=True,
            forwarded=True,
            tags=["IMPORTANT", "work"],
        )
    )
    assert [message.subject for message in found] == ["Matched"]
    assert [message.subject for message in tb.search(unread=True)] == ["Unread"]


def test_unknown_status_does_not_match_unread_filter(tmp_path):
    profile = make_profile(tmp_path)
    write_mbox(
        profile / "Mail" / "Local Folders" / "Inbox",
        [make_message("Unknown")],
    )

    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])
    assert tb.messages()[0].read is None
    assert tb.search(unread=True) == []


def test_invalid_date_is_excluded_from_date_search(tmp_path):
    profile = make_profile(tmp_path)
    write_mbox(
        profile / "Mail" / "Local Folders" / "Inbox",
        [make_message("No date", message_date=False)],
    )

    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])
    assert tb.search(after=date(2026, 1, 1)) == []


def test_limit_validation_and_zero_limit(tmp_path):
    profile = make_profile(tmp_path)
    write_mbox(
        profile / "Mail" / "Local Folders" / "Inbox",
        [make_message("One")],
    )
    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])

    assert tb.messages(limit=0) == []
    assert tb.search(limit=0) == []
    with pytest.raises(ValueError):
        tb.messages(limit=-1)
    with pytest.raises(ValueError):
        tb.search(limit=-1)


def test_message_body_and_attachment_exports(tmp_path):
    message = Message(
        id=1,
        sender="a@example.com",
        recipients="b@example.com",
        subject="Export",
        date="",
        text_body="plain text",
        html_body="<p>html</p>",
    )

    assert message.save_text(tmp_path / "message.txt").read_text() == "plain text"
    assert message.save_html(tmp_path / "message.html").read_text() == "<p>html</p>"


def test_public_version_is_available():
    assert pythonbird.__version__
