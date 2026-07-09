import pytest
from pathlib import Path
from pythonbird.core import ThunderbirdLinux
from pythonbird.mail import ThunderbirdMail
from pythonbird.contacts import ThunderbirdContacts


@pytest.fixture
def mock_thunderbird_profile(tmp_path):
    """Creates a temporary mock Thunderbird profile structure for testing."""
    # 1. Create simulated directories
    profile_dir = tmp_path / "mock_profile.default-release"
    profile_dir.mkdir()

    local_folders = profile_dir / "Mail" / "Local Folders"
    local_folders.mkdir(parents=True)

    # 2. Mock profiles.ini
    ini_path = tmp_path / "profiles.ini"
    ini_content = (
        "[General]\n"
        "StartWithLastProfile=1\n\n"
        "[Profile0]\n"
        "Name=default\n"
        "IsRelative=1\n"
        "Path=mock_profile.default-release\n"
        "Default=1\n"
    )
    ini_path.write_text(ini_content, encoding="utf-8")

    # 3. Mock prefs.js
    prefs_path = profile_dir / "prefs.js"
    prefs_content = (
        'user_pref("mail.identity.id1.useremail", "developer@example.com");\n'
        'user_pref("mail.identity.id2.useremail", "test@example.com");\n'
    )
    prefs_path.write_text(prefs_content, encoding="utf-8")

    # 4. Mock Inbox (mbox format)
    inbox_path = local_folders / "Inbox"
    inbox_content = (
        "From tester@example.com Fri Jul  9 12:00:00 2026\n"
        "From: tester@example.com\n"
        "Subject: Test Subject\n"
        "Date: Fri, 09 Jul 2026 12:00:00 +0000\n"
        "Content-Type: text/plain; charset=utf-8\n\n"
        "Hello from the automated test!\n\n"
    )
    inbox_path.write_text(inbox_content, encoding="utf-8")

    return tmp_path, profile_dir


def test_thunderbird_initialization(monkeypatch, mock_thunderbird_profile):
    """Tests if the core module correctly finds the profile and parses accounts."""
    base_dir, profile_dir = mock_thunderbird_profile

    # Monkeypatch the internal method so it returns our temp test directory
    monkeypatch.setattr(
        ThunderbirdLinux, "_find_thunderbird_dir", lambda self: base_dir
    )

    # Initialize client
    tb = ThunderbirdLinux()

    assert tb.profile_dir == profile_dir
    assert "developer@example.com" in tb.get_mail_accounts()
    assert "test@example.com" in tb.get_mail_accounts()
    assert len(tb.get_mail_accounts()) == 2


def test_mail_reading(monkeypatch, mock_thunderbird_profile):
    """Tests if the mail module successfully extracts and parses local emails."""
    base_dir, _ = mock_thunderbird_profile
    monkeypatch.setattr(
        ThunderbirdLinux, "_find_thunderbird_dir", lambda self: base_dir
    )

    tb = ThunderbirdLinux()
    mail_manager = ThunderbirdMail(tb)
    messages = mail_manager.get_local_inbox_messages()

    assert len(messages) == 1
    assert messages[0]["subject"] == "Test Subject"
    assert "tester@example.com" in messages[0]["from"]
    assert "Hello from the automated test!" in messages[0]["body"]
