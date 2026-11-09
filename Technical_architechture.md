# IP-SAKTI Sahayak — Technical Architecture

## 1. Architecture Overview

The platform should use a modular architecture with a shared evidence retrieval layer and two separate application workflows:

1. Innovation Analysis Engine.
2. Patent Assistant.

Both workflows can reuse document processing, embeddings, vector search, keyword search, source metadata and evidence validation.

However, their orchestration, prompts, outputs and validation requirements must remain separate.

## 2. Proposed Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | Python + Flask initially |
| LLM | Google Gemini |
| Embeddings | intfloat/multilingual-e5-base |
| Vector database | ChromaDB |
| Keyword retrieval | BM25 |
| Retrieval fusion | Reciprocal Rank Fusion |
| Document processing | PyMuPDF, python-docx, openpyxl, python-pptx |
| OCR | Tesseract or suitable OCR alternative |
| Database | Relational database, preferably PostgreSQL or MySQL |
| Background processing | Background job worker |
| API communication | REST APIs |
| Streaming updates | SSE or polling |
| Report generation | PDF and structured HTML/PDF |

The existing implementation must be inspected before changing dependencies or replacing technologies.

## 3. High-Level Architecture

User
  |
  v
React Frontend
  |
  v
Flask REST API
  |
  +-----------------------------+
  |                             |
  v                             v
Innovation Analysis       Patent Assistant
  |                             |
  v                             v
Innovation Parser         Query Orchestrator
  |                             |
  v                             v
Feature Extraction        Intent Classification
  |                             |
  v                             v
Search Query Generator    Conversation Context
  |                             |
  +-------------+---------------+
                |
                v
        Shared Retrieval Engine
                |
        +-------+--------+
        |                |
        v                v
   Vector Search     BM25 Search
        |                |
        +-------+--------+
                |
                v
        Reciprocal Rank Fusion
                |
                v
       Metadata Filtering
                |
                v
       Deduplication
                |
                v
       Evidence Validation
                |
                v
       Relevant Evidence
                |
        +-------+--------+
        |                |
        v                v
  Comparison Engine   Assistant Answer
        |                |
        v                v
  Report Generator   Citation Validator
        |                |
        +-------+--------+
                |
                v
         Database / Reports
                |
                v
          React Frontend

## 4. Knowledge Base Design

### Initial Data Sources

The existing project contains:

- IMPPAT plant information.
- IMPPAT phytochemical information.
- IMPPAT plant-phytochemical associations.
- IMPPAT bioactivity records.
- IMPPAT therapeutic-use associations.
- IMPPAT single-herbal formulations.
- IMPPAT polyherbal formulations.
- Patent-related PDF documents.
- Research paper material.
- Traditional knowledge material.

Do not assume every PDF inside a patents folder is an actual patent.

Classify documents according to their contents and provenance.

### Document Categories

Use explicit document types:

- patent
- research_paper
- traditional_knowledge
- plant_profile
- phytochemical
- bioactivity
- plant_association
- therapeutic_use
- herbal_formulation
- regulatory_document
- general_reference

Preserve the original source and dataset provenance.

### Metadata

Where available, store:

- document_id
- document_type
- source_name
- source_url
- publication_number
- application_number
- title
- author or applicant
- publication_date
- priority_date
- plant_name
- scientific_name
- phytochemical_name
- language
- page_number
- section_name
- chunk_id
- extraction_status
- provenance

Do not fabricate missing metadata.

## 5. Document Ingestion Pipeline

1. Validate file type and size.
2. Check actual file format against extension.
3. Extract text.
4. Apply OCR to scanned documents where required.
5. Record extraction errors and unreadable pages.
6. Preserve page and section information.
7. Classify source type.
8. Normalize metadata.
9. Remove duplicate content while retaining source references.
10. Apply structure-aware chunking.
11. Generate embeddings.
12. Store vectors and metadata in ChromaDB.

Chunking should preserve meaningful boundaries such as patent claims, sections, paragraphs, tables and research-paper sections.

Avoid blindly splitting every document into identical character lengths.

## 6. Retrieval Pipeline

The shared retrieval engine should support:

1. Query normalization.
2. Language identification.
3. Query translation or multilingual semantic handling where needed.
4. Query expansion using botanical names, synonyms and technical terminology.
5. Vector retrieval.
6. BM25 keyword retrieval.
7. Reciprocal Rank Fusion.
8. Metadata filtering.
9. Duplicate removal.
10. Evidence selection.
11. Optional reranking after evaluation.
12. Evidence quality assessment.

For patent searches, preserve document sections such as claims, descriptions and examples.

An abstract-only match must not be treated as sufficient evidence of a technical disclosure.

### Retrieval Evidence Requirements

Every retrieved result should retain:

- Source ID.
- Source type.
- Original text passage.
- Page or section.
- Metadata.
- Retrieval score or rank.
- Original source reference.

Do not send only anonymous text chunks to the LLM.

## 7. Innovation Analysis Engine

### Input

Structured innovation data and user-uploaded documents.

### Processing

#### Stage 1: Input Validation

Check whether essential information is present.

#### Stage 2: Document Extraction

Extract relevant content from uploaded documents.

Keep private submission content separate from external evidence.

#### Stage 3: Innovation Structuring

Extract:

- Ingredients.
- Botanical names.
- Plant parts.
- Quantities and proportions.
- Extraction methods.
- Preparation conditions.
- Formulation type.
- Intended use.
- Technical problem.
- Proposed solution.
- Claimed advantages.
- Distinguishing features.

Use structured output and validate it against a schema.

Unknown details must remain unknown.

#### Stage 4: Feature-Level Query Generation

Generate multiple queries for each technical feature.

Example:

Feature: Turmeric-based formulation prepared using a specific extraction method.

Search separately for:

- Turmeric formulations.
- Curcuma longa extraction methods.
- Relevant plant parts.
- Known phytochemicals.
- Related preparation conditions.
- Related technical applications.

#### Stage 5: Evidence Retrieval

Retrieve from the relevant external knowledge sources.

#### Stage 6: Feature Comparison

Compare each innovation feature against retrieved evidence.

Possible classifications:

- Exact disclosed match.
- Strong technical overlap.
- Partial overlap.
- Conceptual similarity.
- No match identified in searched corpus.
- Inconclusive.

Every classification must have a reason and supporting evidence.

#### Stage 7: Gap Analysis

Identify:

- Already disclosed features.
- Similar but different features.
- Features not found in the searched corpus.
- Missing information in the submitted innovation.
- Areas requiring further investigation.

#### Stage 8: Report Generation

Generate a structured report from validated findings.

#### Stage 9: Citation Validation

Check every factual claim and citation.

#### Stage 10: Save Version

Store a new analysis version without overwriting previous reports.

## 8. Patent Assistant

The Patent Assistant uses the shared retrieval engine but has its own query orchestration and answer-generation workflow.

### Query Classification

Classify incoming messages into:

- Greeting.
- General knowledge.
- AYUSH research question.
- Patent search.
- Innovation-specific question.
- Follow-up question.
- Comparison question.
- Unrelated question.
- Ambiguous question.
- Unsupported question.

### Conversation Context

Maintain:

- Current conversation ID.
- Recent user messages.
- Relevant assistant responses.
- Active innovation ID.
- Active analysis version.
- Referenced sources.
- Current topic.

Conversation history should help interpret follow-up questions.

It must not become a substitute for external evidence.

For example:

User: Which phytochemicals are associated with turmeric?

Assistant: Retrieves and answers with evidence.

User: Which of these have reported bioactivity?

Assistant: Resolves "these" from the previous context and retrieves relevant bioactivity records.

User: What is the capital of Japan?

Assistant: Answers as a general knowledge question without forcing irrelevant patent retrieval.

### Evidence States

Each research answer should be classified as:

- Sufficient evidence.
- Partial evidence.
- Conflicting evidence.
- Insufficient evidence.
- Source unavailable.
- Extraction unreadable.

If evidence is insufficient, the assistant should say so clearly.

### Answer Structure

Where applicable:

1. Direct answer.
2. Explanation.
3. Evidence and citations.
4. Limitations.
5. Suggested next research step.

## 9. Citation Validation

Each generated citation must be checked against stored evidence.

Validate:

- Citation ID exists.
- Source exists.
- Original passage exists.
- Page or section is correct.
- Citation actually supports the claim.
- Source URL or identifier is available where applicable.

Do not invent source titles, publication numbers, page numbers or URLs.

A citation that merely discusses the same topic is not necessarily supporting evidence.

## 10. Report Structure

The report should include:

1. Executive summary.
2. Submitted innovation profile.
3. Document extraction summary.
4. Search methodology.
5. Search sources and coverage.
6. Relevant patent disclosures.
7. Relevant research publications.
8. Traditional knowledge and AYUSH context.
9. Phytochemical findings.
10. Feature-level similarity comparison.
11. Novelty-related observations.
12. Inventive-step research considerations.
13. Technical gaps and risks.
14. Recommendations.
15. Preliminary patent-readiness assessment.
16. References and evidence appendix.

Never declare that an invention is patentable or guarantee novelty.

## 11. Suggested Database Design

Core entities:

- users
- innovations
- innovation_versions
- innovation_documents
- analyses
- analysis_stages
- search_queries
- retrieved_sources
- evidence_records
- comparison_findings
- reports
- conversations
- messages
- message_citations

Use stable IDs and appropriate foreign keys.

Every analysis should reference the exact innovation version it evaluated.

Every report should reference the analysis that generated it.

## 12. Suggested API Design

### Innovations

POST /api/innovations

GET /api/innovations

GET /api/innovations/{innovation_id}

PUT /api/innovations/{innovation_id}

### Analysis

POST /api/innovations/{innovation_id}/analyze

GET /api/analyses/{analysis_id}/status

GET /api/analyses/{analysis_id}/report

GET /api/analyses/{analysis_id}/compare

### Assistant

POST /api/assistant/chat

GET /api/assistant/conversations

GET /api/assistant/conversations/{conversation_id}

GET /api/assistant/conversations/{conversation_id}/messages

Adapt these endpoints to the existing backend where practical.

## 13. Background Processing

Innovation analysis may take longer than a normal API request.

Use a background job architecture.

The frontend should receive genuine backend stage updates through polling or Server-Sent Events.

Example stages:

- Input validation.
- Document extraction.
- Innovation structuring.
- Query generation.
- Retrieval.
- Evidence validation.
- Feature comparison.
- Report generation.
- Citation validation.
- Completed or failed.

Do not simulate successful processing using frontend timers.

HTTP 200 alone does not mean the analysis succeeded.

## 14. Security and Reliability

Implement:

- File size and file type validation.
- Secure document storage.
- API key protection through environment variables.
- User-level authorization.
- Private document isolation.
- Prompt-injection protection.
- Rate limiting where appropriate.
- Error handling and logging.
- Database transaction management.
- Citation validation.
- Source provenance.
- Explicit failure states.

Treat uploaded and retrieved content as untrusted data, never as instructions to the model.

## 15. Evaluation

Build a small verified evaluation set before claiming retrieval quality.

Initial target: 40–60 questions focused on the turmeric corpus.

Measure:

- Recall@K.
- Precision@K.
- MRR.
- nDCG@K.
- Citation precision.
- Citation coverage.
- Answer faithfulness.
- Answer relevance.
- Abstention accuracy.

Use manually verified expected sources and passages.

LLM-based evaluation may supplement, but must not replace, human verification.

## 16. Implementation Rules

- Reuse existing working modules.
- Do not rebuild existing vector databases without approval.
- Do not delete existing ChromaDB collections.
- Do not change embedding models without evaluating compatibility and migration impact.
- Do not mix private innovation documents with external prior-art evidence.
- Keep Innovation Analysis and Patent Assistant workflows separate.
- Share common retrieval and evidence services.
- Implement incrementally.
- Test each stage before integrating the next.
- Explain architectural changes before applying them.

The final implementation must be demonstrably functional, not merely a collection of files and endpoints.