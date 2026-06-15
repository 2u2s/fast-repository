# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-06-15

### Changed

- **BREAKING:** Renamed the repository interfaces so the interface vs.
  implementation distinction reads at a glance:
  - `AbstractCRUDRepository` → `CRUDRepositoryInterface`
  - `AbstractSyncCRUDRepository` → `SyncCRUDRepositoryInterface`

  The implementation bases (`CRUDRepository`, `SyncCRUDRepository`) are
  unchanged. The old names are removed with no compatibility alias; import
  `CRUDRepositoryInterface` / `SyncCRUDRepositoryInterface` instead.

## [0.1.x]

### Added

- Interface-first CRUD repositories for async (`CRUDRepository`) and sync
  (`SyncCRUDRepository`) SQLAlchemy sessions, with the entity captured from the
  generic argument.
- Read methods: `find`, `find_all`, `find_all_paginated`, `count`, `exists`.
- Write methods: `save`, `save_all`, `delete`, `delete_all`, with an
  `autocommit` flag for unit-of-work control.
- Keyword filters with operator suffixes (`in`, `notin`, `ne`, `gt`, `ge`,
  `lt`, `le`, `like`, `ilike`, `is`); unknown columns/operators raise
  `InvalidFilterError`.
- `order_by`, customizable base `stmt`, row locking via `with_for_update`, and
  opt-in soft delete.
- FastAPI pagination integration via `fastapi-pagination`.

[0.2.0]: https://github.com/2u2s/fast-repository/releases/tag/v0.2.0
