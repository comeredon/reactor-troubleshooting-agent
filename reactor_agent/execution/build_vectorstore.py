"""
Execution layer: build and persist a FAISS vector store from process docs.

Loads:
  - Markdown files (direct read)
  - PDF files (pdfplumber, with graceful fallback on failure)

Chunks at 500 chars / 50 overlap, embeds with HuggingFace all-MiniLM-L6-v2
(local, no API key) unless EMBEDDING_PROVIDER=openai is set.

Saves index to .tmp/faiss_index/ (relative to reactor_agent/).
"""

import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FAISS_INDEX_PATH, CHUNK_SIZE, CHUNK_OVERLAP

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_markdown_docs(docs_dir: str) -> list:
    """Return list of (text, metadata) tuples from all .md files."""
    docs = []
    for fname in os.listdir(docs_dir):
        if fname.endswith(".md"):
            fpath = os.path.join(docs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append((text, {"source": fname, "type": "markdown"}))
            print(f"  Loaded markdown: {fname} ({len(text)} chars)")
    return docs


def _load_pdf_docs(docs_dir: str) -> list:
    """Return list of (text, metadata) tuples from all .pdf files."""
    docs = []
    try:
        import pdfplumber
    except ImportError:
        warnings.warn("pdfplumber not installed; skipping PDFs. Run: pip install pdfplumber")
        return docs

    for fname in os.listdir(docs_dir):
        if fname.endswith(".pdf"):
            fpath = os.path.join(docs_dir, fname)
            try:
                text_parts = []
                with pdfplumber.open(fpath) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                full_text = "\n".join(text_parts)
                if full_text.strip():
                    docs.append((full_text, {"source": fname, "type": "pdf"}))
                    print(f"  Loaded PDF: {fname} ({len(full_text)} chars)")
                else:
                    warnings.warn(f"PDF extracted but empty: {fname}")
            except Exception as exc:
                # Self-annealing: log and continue — PDF failure is non-fatal
                warnings.warn(f"Failed to load PDF {fname}: {exc}. Continuing.")

    return docs


def _get_embeddings():
    """Return embeddings model based on EMBEDDING_PROVIDER env var."""
    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        print("  Using OpenAI embeddings")
        return OpenAIEmbeddings()
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print(f"  Using HuggingFace embeddings: {model_name}")
        return HuggingFaceEmbeddings(model_name=model_name)


def build_vectorstore(docs_dir: str, index_path: str | None = None) -> None:
    """
    Build FAISS index from all docs in docs_dir and save to disk.

    Parameters
    ----------
    docs_dir : str
        Directory containing .md and .pdf documentation files.
    index_path : str, optional
        Where to save the FAISS index. Defaults to FAISS_INDEX_PATH from config.
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document

    if index_path is None:
        index_path = os.path.join(BASE_DIR, FAISS_INDEX_PATH)

    os.makedirs(index_path, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, ".tmp"), exist_ok=True)

    print("Loading documents...")
    raw_docs = _load_markdown_docs(docs_dir) + _load_pdf_docs(docs_dir)

    if not raw_docs:
        raise RuntimeError(f"No documents found in: {docs_dir}")

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    documents = []
    for text, metadata in raw_docs:
        chunks = splitter.split_text(text)
        for j, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={**metadata, "chunk": j},
            ))
    print(f"  Total chunks: {len(documents)}")

    # Embed and build FAISS
    print("Building embeddings (this may take a moment for HuggingFace)...")
    embeddings = _get_embeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(index_path)
    print(f"  Saved FAISS index to: {index_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build FAISS vector store")
    parser.add_argument(
        "--docs-dir",
        default=os.path.join(BASE_DIR, "docs"),
        help="Directory with .md and .pdf documents",
    )
    parser.add_argument(
        "--index-path",
        default=os.path.join(BASE_DIR, FAISS_INDEX_PATH),
        help="Output path for FAISS index",
    )
    args = parser.parse_args()
    build_vectorstore(args.docs_dir, args.index_path)
