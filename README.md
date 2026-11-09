# IP-SAKTI Sahayak — Multilingual AYUSH Prior-Art Discovery

A document-grounded research assistant for discovering potentially relevant information across patents, traditional knowledge documents and research papers. Initial answer languages: English, Hindi and Telugu.

> Scope limitation: this tool supports research and evidence discovery. It does not determine patent novelty, patentability, infringement, validity or freedom to operate. Those require claim-focused legal analysis by qualified professionals.

## 1. Architecture

```text
INGESTION / INDEXING (offline or when corpus changes)
PDF / DOCX / TXT / scanned PDF
  -> text extraction (+ optional OCR)
  -> language and document metadata
  -> patent-aware section tagging and chunking
  -> multilingual E5 passage embeddings
  -> ChromaDB (cosine distance)

QUERY TIME
User query (English / Hindi / Telugu)
  -> multilingual query embedding
  -> dense vector retrieval + BM25 lexical retrieval
  -> Reciprocal Rank Fusion
  -> evidence-grounded Gemini prompt
  -> answer with source/page/section/chunk references
```

## 2. Project layout

```text
config.py                 Central configuration
 data/documents/          Put source files here, optionally in subfolders
 data_loader.py           PDF, DOCX and TXT extraction; optional scanned-PDF OCR
 text_chunker.py          Section-aware chunking with source metadata
 embedder.py              Multilingual E5 embeddings
 vector_store.py          Persistent ChromaDB using cosine distance
 ingest.py                 Full corpus ingestion and staged index replacement
 retriever.py              Dense + BM25 + reciprocal-rank fusion
 prompt_builder.py         AYUSH prior-art evidence prompt
 llm_config.py             Gemini configuration and generation
 rag_pipeline.py           Retrieval + generation orchestration
 main.py                   CLI
 chatbot.py                Streamlit UI
 app.py                    Flask JSON API
 verify_pipeline.py        Structural checks (no Gemini key required)
```

## 3. Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Keep `.env` out of version control.

## 4. Add the corpus

Place files under `data/documents/`. Subfolders are supported. Supported formats:
- PDF (text PDFs)
- DOCX
- TXT (UTF-8, invalid bytes are replaced)
- Scanned PDF via optional OCR

Suggested organization:

```text
data/documents/
  patents/
  traditional_knowledge/
  research_papers/
```

Document type is inferred from path, filename and document text. For reliable classification, use these folder names. Patent publication numbers are extracted when recognizable; verify extracted identifiers against the original source.

### OCR for scanned PDFs

Install the Tesseract OCR engine and language data for `eng`, `hin`, and `tel`. Then set:

```env
ENABLE_OCR=true
OCR_LANGUAGES=eng+hin+tel
```

PyMuPDF calls Tesseract for pages where normal text extraction returns no text. OCR quality must be checked manually, especially for old scans, tables, formulas and mixed scripts. Hindi/Telugu OCR is not guaranteed to be accurate simply because the language pack is installed.

## 5. Build the index

```bash
python verify_pipeline.py
python ingest.py
```

Ingestion creates embeddings and builds a staging collection. After the staging index is populated and validated, it replaces the configured IP-SAKTI collection. The NASA collection is not reused: this project uses a separate `vector_store_ip_sakti/` directory and `ip_sakti_ayush_v1` collection by default.

Changing `EMBEDDING_MODEL` requires a complete re-ingestion. Never mix vectors from different embedding models in one collection.

## 6. Run

CLI:

```bash
python main.py
python main.py --query "Compare prior art for turmeric and neem formulations" --language English
```

Streamlit:

```bash
streamlit run chatbot.py
```

Flask API:

```bash
python app.py
```

POST `/api/query`:

```json
{
  "query": "Find prior-art documents describing turmeric and neem together",
  "language": "English"
}
```

GET `/health` reports the active collection and indexed chunk count.

## 7. Important implementation notes

- `multilingual-e5-base` expects `passage: ` prefixes for indexed chunks and `query: ` prefixes for user questions; the embedder applies these consistently.
- The retriever combines dense search and BM25 rankings using Reciprocal Rank Fusion. BM25 is rebuilt from the current ChromaDB corpus at query time; for a large corpus, persist a lexical index rather than rebuilding it for every query.
- Chunking is section-aware at the page/text-unit level and preserves source, page, language, document type and section metadata. It is a baseline, not a complete patent-claim parser. Complex patents with multi-column layouts, claim dependencies, tables or poor OCR need specialized preprocessing.
- Similarity rankings are candidate-discovery signals, not legal novelty scores. Ingredient overlap alone is insufficient: claims, quantities, preparation, dosage form, technical effect, priority date and jurisdiction may matter.
- The initial implementation supports retrieval across English, Hindi and Telugu, but cross-lingual performance must be measured with a manually reviewed evaluation set. Do not claim validated multilingual accuracy without testing.
- Citation references are grounded in retrieved chunk metadata. The generated answer can still misstate a citation; verify each cited passage against the source document before relying on it.

## 8. Recommended evaluation before demonstration

Create 30–100 expert-reviewed queries with known relevant source documents. Measure Recall@5/10, MRR and nDCG for retrieval; separately score answer faithfulness, citation correctness and abstention when evidence is insufficient. Include cross-language pairs (e.g. Telugu query -> English patent) and ingredient synonyms/transliterations.
