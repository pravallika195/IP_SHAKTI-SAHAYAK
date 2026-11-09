# Migration notes from SPACE-KNOWLEDGE-BOT

## Changed
- Replaced NASA-specific data paths, prompts, CLI and UI with IP-SAKTI AYUSH prior-art workflow.
- Added PDF, DOCX and TXT ingestion; optional scanned-PDF OCR through Tesseract.
- Added document type, language, source path, publication number, priority date and publication date metadata extraction (heuristic; verify against source).
- Added patent section-aware chunking and multilingual E5 embeddings.
- Created a separate ChromaDB path and collection using cosine distance; the NASA vector database and NASA PDFs are excluded from this migrated package.
- Added dense + BM25 retrieval combined with Reciprocal Rank Fusion.
- Added evidence-constrained generation instructions and source metadata in outputs.
- Replaced old NASA CLI/Streamlit/Flask behavior with IP-SAKTI interfaces.

## Not yet verified end-to-end
The package was syntax-compiled and the chunker/prompt builder passed a synthetic smoke test. Full ingestion, Chroma retrieval, OCR and Gemini generation were not run because the uploaded archive did not contain the IP-SAKTI documents or a configured Gemini API key, and the execution environment did not have all project dependencies installed.

## Before use
1. Install `requirements.txt`.
2. Copy `.env.example` to `.env` and configure `GEMINI_API_KEY`.
3. Add the user's source corpus to `data/documents/`.
4. For scanned PDFs, install Tesseract and `eng`, `hin`, `tel` language data, then enable OCR.
5. Run `python verify_pipeline.py`, then `python ingest.py`.
6. Validate retrieval and citations against a manually reviewed test set before using outputs for research decisions.
