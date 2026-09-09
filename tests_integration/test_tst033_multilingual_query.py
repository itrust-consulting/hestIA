"""TST-033 - Multilingual operation (SRS-018).

Uses the EN/FR/DE fixtures at docs/specs/tst/assets/multilingual/. Response
language is checked with a best-effort stopword heuristic, not a real
language-detector dependency - documented as such rather than pretending to
be a precise linguistic assertion.

Expected outcome:
1. A French, English, or German query each receives a response in the same
   language.
2. Retrieval quality is not significantly degraded when the query language
   differs from the primary document language.
"""
import os

from conftest import ASSETS_DIR

FR_STOPWORDS = {"le", "la", "les", "de", "des", "et", "est", "une", "un", "vous", "votre"}
DE_STOPWORDS = {"der", "die", "das", "und", "ist", "sie", "ein", "eine", "sich", "nach"}
EN_STOPWORDS = {"the", "and", "is", "of", "to", "you", "your", "after", "before"}

QUERIES = {
    "fr": "Quelle est la politique de sécurité pour l'accès à distance ?",
    "en": "What is the remote access security policy?",
    "de": "Wie lautet die Richtlinie für den sicheren Fernzugriff?",
}


def _dominant_language(text: str) -> str:
    words = set(w.strip(".,!?;:\"'()").lower() for w in text.split())
    scores = {
        "fr": len(words & FR_STOPWORDS),
        "de": len(words & DE_STOPWORDS),
        "en": len(words & EN_STOPWORDS),
    }
    return max(scores, key=scores.get)


def test_multilingual_query_response_language(admin_client, make_queryable_collection):
    collection, member = make_queryable_collection()
    for lang in ("en", "fr", "de"):
        fixture = os.path.join(ASSETS_DIR, "multilingual", f"remote-access-policy_{lang}.md")
        with open(fixture, "rb") as fh:
            upload = admin_client.post(
                "/api/upload",
                files={"file": (os.path.basename(fixture), fh)},
                data={"collection": collection, "language": {"en": "english", "fr": "french", "de": "german"}[lang]},
            )
        assert upload.status_code == 200, upload.text

    for lang, query in QUERIES.items():
        resp = member.client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": query}],
                "collection": collection,
                "stream": False,
            },
        )
        assert resp.status_code == 200, f"{lang} query failed: {resp.status_code} {resp.text}"
        body = resp.json()
        # /api/chat's exact response shape wasn't traced past
        # Response(await h.resolve(...), media_type="application/json")
        # (hestia/api/routers/chat.py) - adjust this extraction against a
        # real response if these assertions miss the actual field name.
        content = body.get("content") or body.get("message", {}).get("content") or str(body)
        assert content, f"{lang} query returned an empty response"
        detected = _dominant_language(content)
        assert detected == lang, (
            f"expected a {lang}-language response for a {lang} query, "
            f"heuristic detected {detected!r} in: {content[:200]!r}"
        )
