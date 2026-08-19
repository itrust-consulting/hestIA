# Known Issues

Lightweight backlog for identified-but-not-yet-fixed risks and gaps. Not a
replacement for the formal requirements/traceability docs under `docs/reqs/`
— entries here are implementation-level findings worth revisiting, not
requirements.

## Open

### Metadata-edit endpoint can null out a document's classification

- **Found:** 2026-08-14, while fixing custom-metadata-key deletion propagation.
- **Where:** `hestia/api/routers/ingestion.py`, `update_document_metadata` route
  (`PATCH /collections/{name}/documents`), around the `matched_levels`/`level`
  computation.
- **What:** The route re-derives a classification level from the edited
  metadata payload the same way ingestion used to:
  ```python
  matched_levels = [...]
  level = max(matched_levels) if matched_levels else None
  ```
  If a user clears/blanks the classification field (or edits metadata in a
  way that no longer contains a resolvable classification label) during a
  post-ingestion metadata edit, `level` becomes `None` and is written
  straight to `access.classification` in Qdrant.
- **Why it matters:** `hestia/application/ingestion.py`'s `ingest()` was
  fixed to default unresolved classification to `Internal` instead of
  `None`, because a Qdrant range filter (`access.classification <=
  max_classification`) excludes points where the field is `null` —
  `classification: None` makes a document silently invisible to every
  classification-filtered RAG search. This route has the same failure mode
  but wasn't part of that fix, so a metadata edit can still reintroduce it
  for an already-working document.
- **Suggested fix:** Apply the same default-to-`Internal` (or whatever
  policy is decided) fallback here instead of `None`, mirroring
  `hestia/application/ingestion.py`'s `Classification.INTERNAL.level` default.
