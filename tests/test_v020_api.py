import json
from email.message import EmailMessage

from pythonbird import Attachment, Contact, Message, Thunderbird
from pythonbird.core import ThunderbirdLinux
from pythonbird.mail import ThunderbirdMail


def make_profile(tmp_path):
    profile = tmp_path / "test.default-release"
    local = profile / "Mail" / "Local Folders"
    local.mkdir(parents=True)
    (profile / "prefs.js").write_text("", encoding="utf-8")

    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "user@example.com"
    message["Subject"] = "Quarterly report"
    message["Date"] = "Fri, 10 Jul 2026 12:00:00 +0000"
    message.set_content("The report is attached.")
    message.add_attachment(
        b"report-data",
        maintype="application",
        subtype="octet-stream",
        filename="report.bin",
    )

    (local / "Inbox").write_bytes(
        b"From sender@example.com Fri Jul 10 12:00:00 2026\n"
        + message.as_bytes()
        + b"\n\n"
    )
    (local / "Sent").write_text("", encoding="utf-8")
    return profile


def test_object_api_search_attachments_and_export(tmp_path):
    profile = make_profile(tmp_path)
    tb = Thunderbird(profile_dir=profile, command=["thunderbird"])

    assert "Inbox" in tb.folders()
    messages = tb.messages()
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].subject == "Quarterly report"
    assert len(messages[0].attachments) == 1
    assert isinstance(messages[0].attachments[0], Attachment)
    assert messages[0].attachments[0].size == len(b"report-data")

    found = tb.search(subject="quarterly", has_attachments=True)
    assert found == messages

    output = tmp_path / "messages.json"
    tb.export_json(output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data[0]["subject"] == "Quarterly report"
    assert data[0]["attachments"][0]["filename"] == "report.bin"


def test_attachment_save_and_message_save_eml(tmp_path):
    attachment = Attachment("note.txt", "text/plain", b"hello")
    saved = attachment.save(tmp_path)
    assert saved.read_bytes() == b"hello"

    message = Message(
        id=1,
        sender="a@example.com",
        recipients="b@example.com",
        subject="Test",
        date="",
        raw_bytes=b"Subject: Test\n\nBody",
    )
    eml = message.save_eml(tmp_path / "message.eml")
    assert eml.read_bytes().startswith(b"Subject: Test")


def test_legacy_dictionary_api_is_preserved(tmp_path):
    profile = make_profile(tmp_path)
    low_level = ThunderbirdLinux(profile_dir=profile, command=["thunderbird"])
    messages = ThunderbirdMail(low_level).get_local_inbox_messages()
    assert isinstance(messages[0], dict)
    assert messages[0]["subject"] == "Quarterly report"
