"""Build the local search index. Requires Ollama and the embed model."""

from app.rag import ensure_index


def main() -> None:
    index = ensure_index()
    print(f"Indexed {index['chunk_count']} chunks with {index['embed_model']}.")


if __name__ == "__main__":
    main()
