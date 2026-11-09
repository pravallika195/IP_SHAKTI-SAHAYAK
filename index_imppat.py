
import json
from pathlib import Path

from vector_store import get_client, add_documents
from embedder import get_embeddings

DATA_FILE = Path("data/processed/imppat_curcuma/curcuma_records.jsonl")
COLLECTION_NAME = "ip_sakti_curcuma_test_v1"
BATCH_SIZE = 64


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    print("Loading processed IMPPAT records...")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]

    if not records:
        raise ValueError("No records found.")

    client = get_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Curcuma longa IMPPAT test collection",
            "hnsw:space": "cosine"
        }
    )

    metric = (collection.metadata or {}).get("hnsw:space")
    if metric != "cosine":
        raise RuntimeError(
            f"Expected cosine distance, found {metric!r}"
        )

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Existing records: {collection.count()}")
    print(f"Records to index: {len(records)}")

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]

        texts = [record["text"] for record in batch]
        ids = [record["id"] for record in batch]

        metadatas = []
        for record in batch:
            metadata = record.get("metadata", {})
            # ChromaDB metadata supports scalar values.
            clean_metadata = {
                key: value
                for key, value in metadata.items()
                if isinstance(value, (str, int, float, bool))
            }
            metadatas.append(clean_metadata)

        embeddings = get_embeddings(
            texts,
            batch_size=32,
            input_type="passage"
        )

        add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            collection=collection
        )

        print(
            f"Indexed {min(start + len(batch), len(records))}"
            f"/{len(records)} records"
        )

    print("\n========== INDEXING COMPLETE ==========")
    print("Collection:", COLLECTION_NAME)
    print("Final record count:", collection.count())

    original = client.get_collection("ip_sakti_ayush_v1")
    print("Original collection count:", original.count())


if __name__ == "__main__":
    main()
