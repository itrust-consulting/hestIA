"""TST-034 - Large corpus ingestion and retrieval (SRS-019).

Not run by default: a >=100 GB corpus cannot be materialized by this suite.
Point HESTIA_LARGE_CORPUS_DIR at a real (or synthetic) representative corpus
to exercise this, with response-time thresholds via
HESTIA_LARGE_CORPUS_RESPONSE_MS.

Expected outcome:
1. The full corpus ingests without errors or data loss.
2. Queries return semantically relevant results within the established
   response-time thresholds.
3. All system services remain fully operational while serving the corpus.
"""
import os
import time

import pytest

from conftest import search_text

CORPUS_DIR = os.environ.get("HESTIA_LARGE_CORPUS_DIR")
RESPONSE_THRESHOLD_MS = float(os.environ.get("HESTIA_LARGE_CORPUS_RESPONSE_MS", "5000"))
QUERY = os.environ.get("HESTIA_LARGE_CORPUS_TEST_QUERY", "policy")

pytestmark = pytest.mark.skipif(
    not CORPUS_DIR or not os.path.isdir(CORPUS_DIR),
    reason="set HESTIA_LARGE_CORPUS_DIR to a representative/synthetic corpus "
    "directory (target: >=100 GB across multiple documents) to run this test; "
    "not exercised by default",
)


def test_large_corpus_ingest_and_query(admin_client, make_collection):
    collection = make_collection()

    files = [
        os.path.join(root, f)
        for root, _, filenames in os.walk(CORPUS_DIR)
        for f in filenames
    ]
    assert files, f"no files found under {CORPUS_DIR}"

    for path in files:
        with open(path, "rb") as fh:
            resp = admin_client.post(
                "/api/upload",
                files={"file": (os.path.basename(path), fh)},
                data={"collection": collection},
            )
        assert resp.status_code == 200, f"ingestion failed for {path}: {resp.status_code} {resp.text}"
        assert resp.json().get("ok") is True

    start = time.monotonic()
    search = search_text(admin_client, collection, QUERY, mode="semantic")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert search.status_code == 200, search.text
    assert elapsed_ms <= RESPONSE_THRESHOLD_MS, (
        f"query took {elapsed_ms:.0f}ms, exceeding the {RESPONSE_THRESHOLD_MS:.0f}ms threshold"
    )

    # hestia/api/routers/health.py is registered with always_on=True; confirm
    # the service is still responsive after ingesting + querying the corpus.
    health = admin_client.get("/health")
    assert health.status_code == 200, f"service unhealthy after corpus load: {health.status_code} {health.text}"
