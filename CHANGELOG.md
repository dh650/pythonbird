# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-07-13

### Added

- High-level `Thunderbird` object-oriented API.
- Typed `Message`, `Attachment`, and `Contact` dataclasses.
- Discovery and resolution of Thunderbird mail folders.
- Message filtering by sender, recipient, subject, body content, date, and attachment presence.
- Attachment metadata and safe attachment saving.
- EML message export and JSON folder export.
- Object-based contact API.
- Tests covering the new API and backward compatibility.

### Changed

- Package version is now 0.2.0.
- Documentation now recommends the high-level API for new projects.

### Compatibility

- The dictionary-based mail API from 0.1.x remains available.
- Existing low-level classes remain publicly exported.

## [0.1.2] - 2026-07-10

### Added

- Support for explicitly selecting a Thunderbird profile directory.
- Support for explicitly supplying a Thunderbird launch command.
- Flatpak profile auto-detection.
- Iterators for memory-efficient Mbox reading.
- Support for reading arbitrary Mbox files.
- Optional message limits.
- MIME header decoding.
- Message body decoding using declared character sets.
- Separate plain-text and HTML message bodies.
- Optional custom SQLite address book paths.
- Strict and non-strict address book error handling.
- `ThunderbirdContactsError`.
- Tests for compose-window safety, message encodings, and contacts.

### Changed

- Thunderbird commands are now stored as argument lists.
- Compose windows are launched without `shell=True`.
- Attachments are validated before opening the compose window.
- Duplicate configured accounts are removed.
- SQLite address books are explicitly opened in read-only mode.
- Address book schemas are validated before contacts are read.
- Minimum supported Python version is now Python 3.9.
- Documentation was updated to describe the current API and safety behavior.

### Fixed

- Potential shell injection when opening a compose window.
- Incorrect decoding of non-UTF-8 email bodies.
- MIME-encoded email headers being returned without decoding.
- Text attachments being treated as message bodies.
- SQLite errors being silently ignored.
- Missing-profile paths being accepted without validation.
- Missing Thunderbird executables being reported only after process launch.
