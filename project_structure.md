# IP-SAKTI Sahayak project structure

```text
IP-SAKTI-Sahayak/
├── config.py
├── data/
│   └── documents/
│       ├── patents/
│       ├── traditional_knowledge/
│       └── research_papers/
├── vector_store_ip_sakti/       # generated ChromaDB persistence
├── data_loader.py               # PDF/DOCX/TXT + optional OCR
├── text_chunker.py              # section-aware chunking
├── embedder.py                  # multilingual E5 passage/query vectors
├── vector_store.py              # ChromaDB cosine index
├── ingest.py                    # staged corpus indexing
├── retriever.py                 # dense + BM25 + RRF
├── prompt_builder.py            # AYUSH evidence prompt
├── llm_config.py                # Gemini configuration
├── rag_pipeline.py              # query orchestration
├── main.py                      # CLI
├── chatbot.py                   # Streamlit interface
├── app.py                       # Flask JSON API
├── verify_pipeline.py           # structural checks
├── requirements.txt
├── .env.example
└── README.md
```

## Three conceptual RAG stages

1. **Ingestion/indexing:** `data_loader.py` -> `text_chunker.py` -> `embedder.py` -> `vector_store.py`, orchestrated by `ingest.py`.
2. **Retrieval:** `retriever.py` uses `embedder.py` and `vector_store.py` for dense retrieval, plus BM25 lexical retrieval and RRF fusion.
3. **Generation:** `prompt_builder.py` -> `llm_config.py`; `rag_pipeline.py` orchestrates retrieval and generation.

The CLI, Flask API and Streamlit app are application interfaces, not additional RAG stages.
