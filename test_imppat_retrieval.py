
from embedder import get_embeddings
from vector_store import get_client

COLLECTION_NAME = "ip_sakti_curcuma_test_v1"

client = get_client()
collection = client.get_collection(COLLECTION_NAME)

queries = [
    "Which phytochemicals are associated with Curcuma longa?",
    "What biological activities are reported for turmeric compounds?",
    "What are the traditional therapeutic uses of turmeric?",
    "Which Ayurvedic formulations contain Curcuma longa?",
]

for query in queries:
    print("\n" + "=" * 80)
    print("QUERY:", query)

    query_embedding = get_embeddings(
        [query],
        input_type="query"
    )[0]

    query_filter = None

    if "therapeutic uses" in query.lower():
        query_filter = {
            "document_type": "traditional_use_reference"
        }

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where=query_filter,
        include=["documents", "metadatas", "distances"]
    )

    for i, (doc, metadata, distance) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ),
        start=1
    ):
        print(f"\nResult {i}")
        print("Type:", metadata.get("document_type"))
        print("Name:", metadata.get("phytochemical_name", "N/A"))
        print("Distance:", round(distance, 4))
        print("Text:", doc[:350])
