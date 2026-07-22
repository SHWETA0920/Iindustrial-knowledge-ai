"""
MODULE 5: ADVANCED RAG PIPELINE
----------------------------------
Upgrades the basic retrieve-then-generate flow with two additions:

1. Multi-query expansion: the LLM rewrites your question 2-3 different ways
   before searching, so you catch relevant chunks that use different
   wording than your original question.
2. Cross-encoder reranking: after gathering candidates from all query
   variants, a second, more accurate (but slower) model re-scores them for
   true relevance before only the best few go to the final LLM call.

This is the same query_answer() interface as before, so app.py and the CLI
both keep working unchanged.

Usage:
    python src/query.py "What does the OISD guideline say about hot work permits?"
"""

import os
import sys
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

INDEX_PATH = "outputs_store/faiss_index.bin"
METADATA_PATH = "outputs_store/metadata.json"

CANDIDATES_PER_QUERY = 8   # how many chunks to pull per query variant, before reranking
FINAL_TOP_K = 5             # how many chunks survive reranking to reach the LLM

_embed_model = None
_rerank_model = None
_groq_client = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        # A small, fast cross-encoder — good relevance/speed tradeoff for a hackathon demo
        _rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _rerank_model


def get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _groq_client


MULTI_QUERY_PROMPT = """Generate 3 alternative phrasings of this question that might
match different wording in a technical industrial document corpus. Keep each one short.
Return ONLY a JSON array of 3 strings, nothing else.

Original question: {question}
"""

GENERATION_PROMPT = """You are an industrial knowledge assistant. Answer using ONLY the retrieved context below.

Retrieved context (ranked by relevance after reranking):
{context_block}

User question: {question}

Respond in this exact structure:

REASONING:
- For each retrieved chunk, one line: why it was relevant or why it was NOT useful (be honest — it's fine to say a chunk didn't help).

ANSWER:
- If the context fully supports an answer, give it directly with inline citations like [source_1].
- If the context is incomplete or missing key information, say explicitly what is missing and do NOT fill the gap with assumed knowledge. Say: "The available documents don't cover X — you may need to consult [suggest doc type]."

CONFIDENCE: high | medium | low
"""


def load_index_and_metadata():
    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        raise FileNotFoundError("No index found. Run 'python src/ingest.py' first.")
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r") as f:
        data = json.load(f)
    return index, data["chunks"], data["metadata"]


def expand_query(question):
    """Ask the LLM for alternative phrasings. Falls back to just the original
    question if generation fails, so the pipeline never breaks on this step."""
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": MULTI_QUERY_PROMPT.format(question=question)}],
            temperature=0.4,
        )
        text = response.choices[0].message.content.strip()
        text = text.strip("`").replace("json", "", 1).strip() if text.startswith("```") else text
        variants = json.loads(text)
        if isinstance(variants, list):
            return [question] + [v for v in variants if isinstance(v, str)]
    except Exception:
        pass
    return [question]


def retrieve_candidates(queries, model, index, chunks, metadata, per_query=CANDIDATES_PER_QUERY):
    """Search FAISS once per query variant, merge and de-duplicate results."""
    seen_chunk_ids = set()
    candidates = []

    for q in queries:
        q_embedding = model.encode([q], convert_to_numpy=True).astype("float32")
        distances, indices = index.search(q_embedding, per_query)
        for idx in indices[0]:
            if idx < 0:
                continue
            chunk_id = metadata[idx]["chunk_id"]
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            candidates.append({
                "text": chunks[idx],
                "source": metadata[idx]["source"],
                "page": metadata[idx]["page"],
                "category": metadata[idx].get("category", "General")
            })

    return candidates


def rerank(question, candidates, top_k=FINAL_TOP_K):
    """Cross-encoder scores (question, chunk) pairs directly — much more
    accurate than embedding similarity alone, at the cost of being slower,
    which is why it only runs on the smaller candidate set, not the whole index."""
    if not candidates:
        return []

    reranker = get_rerank_model()
    pairs = [[question, c["text"]] for c in candidates]
    scores = reranker.predict(pairs)

    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)

    ranked = sorted(candidates, key=lambda c: -c["rerank_score"])
    return ranked[:top_k]


def generate_answer(question, ranked_chunks):
    client = get_groq_client()

    context_block = "\n\n".join(
        f"[source_{i+1}: {c['source']}, page {c['page']}]\n{c['text']}"
        for i, c in enumerate(ranked_chunks)
    )

    prompt = GENERATION_PROMPT.format(context_block=context_block, question=question)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


def query_answer(question):
    """
    Full pipeline, callable from app.py or the CLI below.
    Returns a dict with the answer text and the supporting chunk metadata,
    so the frontend can render citations without re-parsing the LLM's prose.
    """
    index, chunks, metadata = load_index_and_metadata()
    model = get_embed_model()

    query_variants = expand_query(question)
    candidates = retrieve_candidates(query_variants, model, index, chunks, metadata)
    ranked = rerank(question, candidates)
    answer_text = generate_answer(question, ranked)

    return {
        "question": question,
        "query_variants": query_variants,
        "sources": [{"source": c["source"], "page": c["page"], "score": round(c["rerank_score"], 3)} for c in ranked],
        "answer": answer_text
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python src/query.py "your question here"')
        sys.exit(1)

    question = sys.argv[1]
    print("Expanding query and retrieving candidates...")
    result = query_answer(question)

    print(f"\nQuery variants used: {result['query_variants']}")
    print("\n--- Reranked sources ---")
    for i, s in enumerate(result["sources"]):
        print(f"[{i+1}] {s['source']} (page {s['page']}, rerank score {s['score']})")

    print("\n--- Response ---")
    print(result["answer"])


if __name__ == "__main__":
    main()
