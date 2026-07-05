"""NLP worker — sentence-transformers text similarity."""
from __future__ import annotations

import os
import sys

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from workers.celery_app import celery_app
from workers.utils import finalize_worker_result


@celery_app.task(name="workers.nlp_worker.check_similarity", bind=True, max_retries=2)
def check_similarity(self, session_id: str, text: str, reference_corpus: list[str] | None = None) -> dict:
    similarity_score = 0.0
    matched_source = None

    try:
        from sentence_transformers import SentenceTransformer, util

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        corpus = reference_corpus or [
            "ChatGPT can help you with this assignment",
            "Copy the answer from Chegg",
            "Here is the solution from Stack Overflow",
        ]

        if not text.strip():
            return {"session_id": session_id, "status": "ok", "similarity_score": 0}

        emb_query = model.encode(text, convert_to_tensor=True)
        emb_corpus = model.encode(corpus, convert_to_tensor=True)
        scores = util.cos_sim(emb_query, emb_corpus)[0]
        best_idx = int(scores.argmax())
        similarity_score = float(scores[best_idx])

        if similarity_score >= 0.75:
            matched_source = corpus[best_idx]
    except Exception:
        # Fallback: simple keyword overlap
        suspicious = ["chatgpt", "chegg", "stackoverflow", "copy paste answer"]
        lower = text.lower()
        hits = [k for k in suspicious if k in lower]
        if hits:
            similarity_score = 0.8
            matched_source = hits[0]

    if similarity_score < 0.75:
        return {"session_id": session_id, "status": "ok", "similarity_score": similarity_score}

    payload = {
        "similarity_score": similarity_score,
        "matched_source": matched_source,
    }
    return finalize_worker_result(session_id, "text_similarity", payload)
