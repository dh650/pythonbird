# Changelog

All notable changes to this project are documented in this file.

## [0.3.0] - 2026-07-21

### Added

- Lazy `iter_search_messages()` and high-level `iter_search()` APIs.
- Search filters for unread state, starred, replied, forwarded, and Thunderbird tags.
- Read-only parsing of `X-Mozilla-Status` and `X-Mozilla-Keys` metadata.
- `read`, `starred`, `replied`, `forwarded`, and `tags` fields on `Message`.
- `Message.save_attachments()` for safely saving all attachments.
- `Message.save_text()` and `Message.save_html()` exports.
- Public `pythonbird.__version__` value.
- Tests for nested folders, ambiguous names, metadata filters, invalid dates, limit validation, and body exports.

### Changed

- Nested `.sbd` folders now use stable canonical names such as `Archive/2026`.
- Folder resolution accepts canonical names and unique short names, while rejecting ambiguous short names.
- Search with date filters now excludes messages whose date is absent or invalid.
- Limit validation is consistent across reading, searching, and exporting APIs.
- `Message.to_dict()` now includes read-only flags and tags while retaining legacy keys.
- README and GUIDE now document the complete 0.3.0 API and safety model.
- Package version is now 0.3.0.

### Fixed

- Incorrect nested-folder detection caused by checking for a literal `.sbd` path component.
- Potentially inconsistent folder names between discovery and resolution.
- Search limits of zero being handled only after unnecessary mailbox work.
- Time-zone-aware and naive date comparisons causing type errors in mixed inputs.

### Safety

- Mbox flags and tags remain read-only. pythonbird does not modify message stores or Thunderbird index files.
- Bulk attachment saving checks duplicate and existing destinations before writing.

### Compatibility

- Existing high-level 0.2.x methods remain available.
- The dictionary-based mail API from 0.1.x remains available.
- Existing low-level classes remain publicly exported.

## [0.2.0] - 2026-07-13

This section covers the 0.2.x object-API series, including its maintenance releases through 0.2.2.

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

- Documentation recommends the high-level API for new projects.

### Compatibility

- The dictionary-based mail API from 0.1.x remains available.
- Existing low-level classes remain publicly exported.

## [0.1.2] - 2026-07-10

### Added

- Explicit Thunderbird profile selection and launch-command configuration.
- Flatpak profile auto-detection.
- Memory-efficient Mbox iterators and arbitrary Mbox reading.
- Optional message limits.
- MIME header and body charset decoding.
- Separate plain-text and HTML message bodies.
- Custom SQLite address-book paths and strict/non-strict error handling.
- Additional automated tests.

### Changed

- Compose windows are launched without `shell=True`.
- Attachment paths are validated before launch.
- Duplicate configured accounts are removed.
- SQLite address books are opened read-only and their schemas are validated.
- Minimum supported Python version is Python 3.9.

### Fixed

- Potential shell injection in compose-window launching.
- Incorrect decoding of non-UTF-8 messages and MIME-encoded headers.
- Text attachments being treated as message bodies.
- SQLite errors being silently ignored.
