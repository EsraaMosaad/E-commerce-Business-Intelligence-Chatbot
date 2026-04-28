#!/usr/bin/env python3
"""
backend_rag.py — E-commerce Business Intelligence Chatbot RAG Backend
Person 2 & Person 3 Collaboration

This script implements a lightweight RAG (Retrieval-Augmented Generation) layer
that augments chatbot responses with curated business knowledge for SWOT and
competitor comparison queries.

How it works:
1. Loads knowledge base files (company profiles, market trends)
2. Chunks documents into passages and embeds them using sentence-transformers
3. Indexes embeddings with FAISS for fast nearest-neighbor retrieval
4. At query time: detects if query needs RAG context, retrieves top-k passages
5. Augments the prompt with retrieved context before sending to Ollama

Usage:
    python backend_rag.py
    # Then visit http://localhost:3000 (OpenWebUI) or call the API directly

Required packages:
    pip install faiss-cpu sentence-transformers requests
"""

import os
import re
import json
import requests
import numpy as np

# ──────────────────────────────────────────────
# RAG Dependencies (install if missing)
# ──────────────────────────────────────────────
try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Installing RAG dependencies...")
    os.system("pip install faiss-cpu sentence-transformers requests")
    import faiss
    from sentence_transformers import SentenceTransformer

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "ecom-chatbot"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, 384-dim embeddings
CHUNK_SIZE = 300  # Characters per passage
TOP_K = 3         # Number of context passages to retrieve

# Business keywords that trigger RAG retrieval
BUSINESS_KEYWORDS = [
    "swot", "SWOT",
    "competitor", "compare", "comparison",
    "amazon", "alibaba", "walmart",
    "trends", "market trend",
    "pricing", "delivery", "logistics",
    "strength", "weakness", "opportunity", "threat",
    "e-commerce", "ecommerce",
    "prime", "marketplace", "fulfillment",
]

# ──────────────────────────────────────────────
# RAG Knowledge Base
# ──────────────────────────────────────────────

def load_knowledge_files():
    """
    Loads all markdown knowledge files from the knowledge/ directory.
    Each file contains curated business intelligence on a specific topic.
    """
    knowledge_files = [
        "amazon_profile.md",
        "alibaba_profile.md",
        "walmart_profile.md",
        "market_trends.md",
    ]

    all_chunks = []
    sources = []

    for filename in knowledge_files:
        filepath = os.path.join(KNOWLEDGE_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

            # Chunk the document into passages of CHUNK_SIZE characters
            chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
            all_chunks.extend(chunks)
            sources.extend([filename] * len(chunks))
            print(f"  Loaded {len(chunks)} chunks from {filename}")
        else:
            print(f"  WARNING: {filepath} not found — skipping")

    print(f"\nTotal knowledge chunks: {len(all_chunks)}")
    return all_chunks, sources


def build_faiss_index(chunks, embedding_model_name=EMBEDDING_MODEL):
    """
    Builds a FAISS index from embedded knowledge chunks.
    Uses L2 (Euclidean) distance for nearest-neighbor search.
    """
    print(f"\nLoading embedding model: {embedding_model_name}...")
    embedder = SentenceTransformer(embedding_model_name)

    print(f"Embedding {len(chunks)} knowledge chunks...")
    embeddings = embedder.encode(chunks, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    # Build FAISS index with L2 distance
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    print(f"FAISS index built: {index.ntotal} vectors, {dimension}-dimensional")
    return index, embedder, chunks


def retrieve_context(query, index, embedder, chunks, sources, top_k=TOP_K):
    """
    Retrieves the top-k most relevant knowledge passages for a given query.
    Returns the concatenated context string with source attribution.
    """
    query_embedding = embedder.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, top_k)

    # Collect unique chunks (avoid repetition)
    seen = set()
    context_parts = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(chunks) and chunks[idx] not in seen:
            seen.add(chunks[idx])
            context_parts.append(f"[Source: {sources[idx]}]\n{chunks[idx]}")

    if not context_parts:
        return ""

    return "\n\n".join(context_parts)


def needs_rag(query):
    """
    Determines whether a query should trigger RAG retrieval.
    Returns True if any business keyword is found in the query.
    """
    query_lower = query.lower()
    return any(keyword.lower() in query_lower for keyword in BUSINESS_KEYWORDS)


def build_augmented_prompt(query, context=""):
    """
    Builds the full prompt sent to Ollama, including RAG context if available.
    Uses the same format as the fine-tuning instruction template.
    """
    system = (
        "You are an expert e-commerce business intelligence analyst. "
        "You specialize in SWOT analyses, competitor comparisons, and market trend reports. "
        "Provide structured, concise, and evidence-based responses."
    )

    if context:
        prompt = (
            f"<|system|>{system}\n"
            f"<|user|>{query}\n\n"
            f"[Context — retrieved from knowledge base]:\n{context}\n\n"
            f"<|assistant|>"
        )
    else:
        prompt = (
            f"<|system|>{system}\n"
            f"<|user|>{query}\n"
            f"<|assistant|>"
        )

    return prompt


def chat_with_model(prompt, model_name=MODEL_NAME, temperature=0.3, max_tokens=512):
    """
    Sends a prompt to the Ollama API and returns the model's response.
    """
    payload = {
        "model": model_name,
        "prompt": prompt,
        "temperature": temperature,
        "top_p": 0.9,
        "num_ctx": 2048,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Make sure Ollama is running on localhost:11434."
    except Exception as e:
        return f"ERROR: {str(e)}"


def chat(user_query, index=None, embedder=None, chunks=None, sources=None):
    """
    Main chat function: determines if RAG is needed, retrieves context,
    augments prompt, and returns the model response.
    """
    print(f"\n[CHAT] User: {user_query[:80]}...")

    if index is not None and needs_rag(user_query):
        print("[RAG] Triggered — retrieving business knowledge...")
        context = retrieve_context(user_query, index, embedder, chunks, sources)
        print(f"[RAG] Retrieved {len(context)} chars of context")
    else:
        context = ""
        print("[RAG] Not needed for this query type")

    prompt = build_augmented_prompt(user_query, context)
    response = chat_with_model(prompt)

    print(f"[CHAT] Bot: {response[:100]}...")
    return response


# ──────────────────────────────────────────────
# Ollama API Test Function
# ──────────────────────────────────────────────

def test_ollama_connection():
    """Tests if Ollama is running and the model is available."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama connected. Available models: {[m['name'] for m in models]}")
            return True
    except Exception as e:
        print(f"❌ Ollama not reachable: {e}")
        return False


# ──────────────────────────────────────────────
# CLI Chat Interface
# ──────────────────────────────────────────────

def run_cli():
    """
    Interactive CLI chat interface.
    Type your query and press Enter. Type 'exit' to quit.
    Type 'test' to run built-in test queries.
    """
    print("=" * 60)
    print("E-commerce BI Chatbot — RAG CLI")
    print("=" * 60)
    print("Initializing RAG knowledge base...")

    # Build index
    chunks, sources = load_knowledge_files()
    index, embedder, chunks_list = build_faiss_index(chunks)

    print("\nInitializing Ollama connection...")
    test_ollama_connection()

    print("\n" + "=" * 60)
    print("Chat ready! Type your query (or 'test' for demo, 'exit' to quit)")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            elif user_input.lower() == "test":
                test_queries = [
                    "Give me a SWOT analysis for Amazon in e-commerce.",
                    "Compare Amazon and Walmart on logistics.",
                    "What are the top e-commerce market trends?",
                    "Summarize customer complaints about electronics delivery.",
                ]
                for q in test_queries:
                    chat(q, index, embedder, chunks_list, sources)
                    print()
            else:
                response = chat(user_input, index, embedder, chunks_list, sources)
                print(f"\nBot: {response}")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli()
    else:
        print("""
╔══════════════════════════════════════════════════════════════╗
║  E-commerce BI Chatbot — RAG Backend                        ║
║  Usage: python backend_rag.py --cli                          ║
║         (Starts interactive CLI chat with RAG enabled)       ║
║                                                              ║
║  Prerequisites:                                              ║
║    1. Ollama running:  ollama serve                         ║
║    2. Model loaded:     ollama run ecom-chatbot             ║
║    3. Dependencies:      pip install faiss-cpu sentence-     ║
║                         transformers requests                ║
╚══════════════════════════════════════════════════════════════╝
        """)
