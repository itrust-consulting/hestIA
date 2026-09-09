"""TST-042 - Hybrid retrieval mode comparison (SRS-024).

Uses docs/specs/tst/assets/hybrid_retrieval/api-access-controls.md, written
so semantic and keyword search diverge: it contains the exact term
"PKCE" once, plus a longer passage about endpoint authorization that never
uses that term but is conceptually related.

Expected outcome:
1. Semantic mode ranks passages by vector similarity.
2. Keyword mode ranks passages by BM25 term frequency.
3. Hybrid mode combines both scores and returns a merged, re-ranked result set.
4. All three modes are accessible via /search and via /chat, /generate when
   a collection is specified.
"""
import os

from conftest import ASSETS_DIR, search_text


def test_search_modes_return_results(admin_client, make_collection):
    collection = make_collection()
    fixture = os.path.join(ASSETS_DIR, "hybrid_retrieval", "api-access-controls.md")
    with open(fixture, "rb") as fh:
        upload = admin_client.post(
            "/api/upload",
            files={"file": ("api-access-controls.md", fh)},
            data={"collection": collection},
        )
    assert upload.status_code == 200, upload.text

    keyword_resp = search_text(admin_client, collection, "PKCE", mode="keyword")
    assert keyword_resp.status_code == 200, keyword_resp.text
    assert keyword_resp.json().get("data"), "keyword search returned no data"

    semantic_resp = search_text(
        admin_client, collection,
        "how does the API stop a client from escalating its own privileges",
        mode="semantic",
    )
    assert semantic_resp.status_code == 200, semantic_resp.text
    assert semantic_resp.json().get("data"), "semantic search returned no data"

    hybrid_resp = search_text(admin_client, collection, "PKCE authorization", mode="hybrid")
    assert hybrid_resp.status_code == 200, hybrid_resp.text
    assert hybrid_resp.json().get("data"), "hybrid search returned no data"


def test_modes_accessible_via_chat_and_generate(admin_client, make_queryable_collection):
    """SRS-024 AC4: all three modes must also be reachable via /chat and
    /generate when a collection is specified - passed through query_kwargs
    (ChatRequest.query_kwargs / GenerateRequest.query_kwargs). Unlike
    /api/search, /api/chat and /api/generate enforce CollectionAccessPolicy
    (hestia/domain/policies/guard.py) with no admin bypass, so the querying
    client here must be a real tenant member (make_queryable_collection),
    not admin_client - ingestion still goes through admin_client since
    assert_collection_moderator does bypass for is_admin."""
    collection, member = make_queryable_collection()
    fixture = os.path.join(ASSETS_DIR, "hybrid_retrieval", "api-access-controls.md")
    with open(fixture, "rb") as fh:
        upload = admin_client.post(
            "/api/upload",
            files={"file": ("api-access-controls.md", fh)},
            data={"collection": collection},
        )
    assert upload.status_code == 200, upload.text

    for mode in ("semantic", "keyword", "hybrid"):
        chat_resp = member.client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "What is PKCE?"}],
                "collection": collection,
                "query_kwargs": {"mode": mode},
                "stream": False,
            },
        )
        assert chat_resp.status_code == 200, f"chat with mode={mode} failed: {chat_resp.text}"

        gen_resp = member.client.post(
            "/api/generate",
            json={"prompt": "What is PKCE?", "collection": collection, "query_kwargs": {"mode": mode}},
        )
        assert gen_resp.status_code == 200, f"generate with mode={mode} failed: {gen_resp.text}"
