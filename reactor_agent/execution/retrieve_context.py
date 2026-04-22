"""
Execution layer: retrieve relevant context from FAISS vector store.
Returns top-K document chunks with source metadata.
"""

import os
import sys
import warnings
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FAISS_INDEX_PATH, RAG_TOP_K

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_embeddings():
    """Return embeddings model matching what was used at build time."""
    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(model_name=model_name)


def retrieve_context(
    query: str,
    index_path=None,
    top_k: int = RAG_TOP_K,
) -> List[Dict]:
    """
    Query the FAISS index and return top-K chunks with metadata.

    Parameters
    ----------
    query : str
        Natural language query describing the anomaly / question.
    index_path : str, optional
        Path to the saved FAISS index directory.
    top_k : int
        Number of chunks to return.

    Returns
    -------
    List[dict]  — each dict has keys: "content", "source", "chunk", "score"
    """
    from langchain_community.vectorstores import FAISS

    if index_path is None:
        index_path = os.path.join(BASE_DIR, FAISS_INDEX_PATH)

    if not os.path.isdir(index_path):
        raise FileNotFoundError(
            f"FAISS index not found at: {index_path}\n"
            "Run: python execution/build_vectorstore.py"
        )

    embeddings = _get_embeddings()
    vectorstore = FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    results = vectorstore.similarity_search_with_score(query, k=top_k)

    chunks = []
    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "chunk": doc.metadata.get("chunk", 0),
            "score": round(float(score), 4),
        })

    return chunks


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query FAISS vector store")
    parser.add_argument("query", help="Query string")
    parser.add_argument("--index-path", default=None)
    parser.add_argument("--top-k", type=int, default=RAG_TOP_K)
    args = parser.parse_args()

    chunks = retrieve_context(args.query, args.index_path, args.top_k)
    for i, c in enumerate(chunks, 1):
        print(f"\n--- Chunk {i} | source={c['source']} | score={c['score']} ---")
        print(c["content"][:300])
