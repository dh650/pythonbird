import os
import re
import shutil
import subprocess
import configparser
from pathlib import Path


class ThunderbirdLinux:
    def __init__(self):
        self.base_dir = self._find_thunderbird_dir()
        self.profile_dir = self._get_active_profile_dir()
        self.prefs = self._parse_prefs()
        self.cmd = self._detect_system_command()

    def _find_thunderbird_dir(self) -> Path:
        """Locates the root Thunderbird directory on Linux."""
        standard_path = Path.home() / ".thunderbird"
        snap_path = Path.home() / "snap" / "thunderbird" / "common" / ".thunderbird"

        if standard_path.exists():
            return standard_path
        elif snap_path.exists():
            return snap_path
        else:
            raise FileNotFoundError(
                "Thunderbird directory not found (checked APT/RPM and Snap paths)."
            )

    def _get_active_profile_dir(self) -> Path:
        """Determines the active/default profile directory using profiles.ini."""
        ini_path = self.base_dir / "profiles.ini"
        if not ini_path.exists():
            raise FileNotFoundError("profiles.ini file is missing.")

        config = configparser.ConfigParser()
        config.read(ini_path)

        for section in config.sections():
            if (
                section.startswith("Profile")
                and config.get(section, "Default", fallback="0") == "1"
            ):
                is_relative = config.getint(section, "IsRelative", fallback=1)
                path_value = config.get(section, "Path")

                if is_relative:
                    return self.base_dir / path_value
                return Path(path_value)

        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.endswith(".default-release"):
                return item

        raise FileNotFoundError("Could not determine the active Thunderbird profile.")

    def _parse_prefs(self) -> dict:
        """Parses the prefs.js configuration file using regex."""
        prefs_path = self.profile_dir / "prefs.js"
        prefs = {}
        if not prefs_path.exists():
            return prefs

        pattern = re.compile(
            r'user_pref\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']?([^"\')]+)["\']?\s*\);'
        )

        with open(prefs_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    key, value = match.groups()
                    prefs[key] = value.strip("\"'")
        return prefs

    def _detect_system_command(self) -> str:
        """Detects how Thunderbird is installed to trigger CLI commands."""
        if shutil.which("thunderbird"):
            return "thunderbird"
        elif (
            shutil.which("flatpak")
            and subprocess.run(
                ["flatpak", "info", "org.mozilla.Thunderbird"], capture_output=True
            ).returncode
            == 0
        ):
            return "flatpak run org.mozilla.Thunderbird"
        return "thunderbird"

    def get_mail_accounts(self) -> list:
        """Returns a list of configured email addresses."""
        accounts = []
        for key, val in self.prefs.items():
            if key.startswith("mail.identity.") and key.endswith(".useremail"):
                accounts.append(val)
        return accounts

    def open_compose_window(
        self, to: str, subject: str, body: str, attachment_path: str = None
    ):
        """Opens the Thunderbird composition window with pre-filled fields."""
        compose_args = f"to='{to}',subject='{subject}',body='{body}'"
        if attachment_path:
            compose_args += f",attachment='{attachment_path}'"

        full_command = f'{self.cmd} -compose "{compose_args}"'
        subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
