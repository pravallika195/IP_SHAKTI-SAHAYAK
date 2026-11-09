"""Innovation Analysis Engine for IP-SAKTI Sahayak.

Performs structured prior-art discovery, feature-by-feature comparison,
and research gap analysis for AYUSH innovations against indexed patent
and traditional knowledge corpora (IMPPAT).

Strictly adheres to:
1. Evidence-grounded comparison with 4-field citations.
2. Honest reporting of undisclosed or missing features.
3. Explicit disclaimer that semantic search does NOT prove novelty or patentability.
4. Identification of Indian Patents Act considerations (Section 3(p), Section 3(e)).
5. Separate evaluation of each technical feature, distinguishing ingredient matches
   from formulation/method matches.
6. Clear distinction between user-provided unverified claims and external verified evidence.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any

from config import TOP_K
from llm_config import configure_llm, generate_response
from rag_pipeline import RAGPipeline
from retriever import retrieve_multi

logger = logging.getLogger(__name__)

INNOVATION_ANALYSIS_SYSTEM_PROMPT = """You are the Senior Patent & AYUSH Prior-Art Research Analyst for IP-SAKTI Sahayak.

Your role is to conduct an objective, feature-by-feature prior-art comparison of a proposed AYUSH innovation against retrieved documentary evidence from patent filings, traditional formulations (AFI/API), and scientific phytochemistry datasets (IMPPAT).

CRITICAL GROUND RULES:
1. ONLY make assertions that are supported by the provided EXTERNALLY RETRIEVED EVIDENCE.
2. Distinguish applicant claims from verified evidence: The user-submitted problem, solution, and claimed advantages are UNVERIFIED APPLICANT CLAIMS. Never treat applicant assertions as prior art.
3. NEVER claim or certify that an innovation is "novel", "patentable", or "inventive". Semantic search or absence of evidence in a database does NOT legally establish patentability.
4. Every factual comparison must cite supporting evidence using the exact 4-field format:
   [source_name, page_number, section_name, chunk_id]
   For IMPPAT records, use [IMPPAT, N/A, formulation/traditional_use, chunk_id] or [IMPPAT, N/A, phytochemical, chunk_id].
5. Evaluate EVERY submitted technical feature SEPARATELY. Do not combine, merge, or omit features.
6. Categorize each technical feature into one of:
   - "KNOWN_IN_PRIOR_ART": The specific technical parameter, complete formulation, or extraction method is explicitly documented in the retrieved evidence.
   - "PARTIAL_OVERLAP": An ingredient or therapeutic target is known, BUT the specific formulation matrix, delivery system, concentration, or preparation method is NOT disclosed in the retrieved evidence. Crucially, distinguish an ingredient-only match from a complete formulation or method match.
   - "NOT_FOUND_IN_CORPUS": The feature is not found in the searched pilot knowledge base. Explicitly state that this status applies ONLY to the searched pilot database and does not prove global novelty.
7. Highlight Indian Patents Act statutory requirements:
   - Section 3(p): Inventions which are essentially traditional knowledge or an aggregation/duplication of known properties are not patentable.
   - Section 3(e): A substance obtained by a mere admixture resulting only in the aggregation of properties is not patentable without demonstrating synergistic efficacy beyond mere additive effects.
"""


class InnovationAnalysisEngine:
    """Orchestrates structured feature extraction, multi-query retrieval, and prior-art comparison."""

    def __init__(self, top_k: int = TOP_K, collections: list[str] | None = None):
        self.top_k = top_k
        self.collections = collections or ["ip_sakti_ayush_v1", "ip_sakti_curcuma_test_v1"]
        self.system_prompt = INNOVATION_ANALYSIS_SYSTEM_PROMPT
        self.model = configure_llm(self.system_prompt)
        self._rag_validator = RAGPipeline(top_k=top_k, model=self.model)

    def _normalize_input(self, innovation: dict[str, Any]) -> dict[str, Any]:
        """Normalizes and validates innovation input fields.

        Validates required fields and rejects empty inputs with ValueError.
        Does NOT fabricate default ingredients, features, or claimed advantages.
        """
        title = str(innovation.get("title", "")).strip()
        if not title:
            raise ValueError("Innovation title is required.")

        ayush_system = str(innovation.get("ayush_system", "Ayurveda")).strip()

        # Normalize ingredients
        raw_ingredients = innovation.get("ingredients", [])
        if isinstance(raw_ingredients, str):
            ingredients = [i.strip() for i in re.split(r"[,\n;]+", raw_ingredients) if i.strip()]
        elif isinstance(raw_ingredients, (list, tuple)):
            ingredients = [str(i).strip() for i in raw_ingredients if str(i).strip()]
        else:
            ingredients = []

        if not ingredients:
            raise ValueError("At least one ingredient or botanical substance is required.")

        # Normalize technical features
        raw_features = innovation.get("technical_features", [])
        if isinstance(raw_features, str):
            features = [f.strip("- *•\t") for f in raw_features.split("\n") if f.strip("- *•\t")]
        elif isinstance(raw_features, (list, tuple)):
            features = [str(f).strip("- *•\t") for f in raw_features if str(f).strip("- *•\t")]
        else:
            features = []

        if not features:
            raise ValueError("At least one technical feature is required for prior-art comparison.")

        # Optional fields: record honestly without fabricating claims
        problem = str(innovation.get("problem", "")).strip() or "Not specified by applicant"
        solution = str(innovation.get("solution", "")).strip() or "Not specified by applicant"
        claimed_advantages = str(innovation.get("claimed_advantages", "")).strip() or "None specified by applicant"

        # Optional applicant-uploaded documentation & extracted text (Unverified private submission)
        raw_docs = innovation.get("uploaded_documents") or innovation.get("documents") or []
        uploaded_documents = []
        if isinstance(raw_docs, list):
            for doc in raw_docs:
                if isinstance(doc, dict):
                    uploaded_documents.append({
                        "document_id": str(doc.get("document_id") or doc.get("id") or ""),
                        "filename": str(doc.get("filename") or doc.get("original_filename") or "document"),
                        "page_count": int(doc.get("page_count") or 1),
                        "file_type": str(doc.get("file_type") or ""),
                        "extracted_text": str(doc.get("extracted_text") or doc.get("text") or "")[:15000],
                        "warnings": doc.get("warnings") or []
                    })

        document_text = str(innovation.get("document_text", "")).strip()

        return {
            "title": title,
            "ayush_system": ayush_system,
            "problem": problem,
            "solution": solution,
            "ingredients": ingredients,
            "technical_features": features,
            "claimed_advantages": claimed_advantages,
            "uploaded_documents": uploaded_documents,
            "document_text": document_text
        }

    def generate_search_queries(self, data: dict[str, Any]) -> list[str]:
        """Generates targeted sub-queries covering botanical, formulation, patent, and EVERY technical feature."""
        queries: list[str] = []
        ingr_str = " ".join(data["ingredients"][:3])

        # 1. Botanical & phytochemical query
        queries.append(f"{ingr_str} phytochemicals bioactivities therapeutic uses")

        # 2. Traditional formulation & therapeutic indication query
        problem_words = re.findall(r"\b[A-Za-z]{4,}\b", data["problem"])
        problem_kw = " ".join(problem_words[:3]) if problem_words else "medicinal use"
        queries.append(f"{ingr_str} formulation {data['ayush_system']} {problem_kw}".strip())

        # 3. Patent & technical claim query
        sol_words = re.findall(r"\b[A-Za-z]{4,}\b", data["solution"])
        sol_kw = " ".join(sol_words[:3]) if sol_words else "composition extract"
        queries.append(f"patent claims {ingr_str} extract {sol_kw}".strip())

        # 4. Targeted queries for EVERY submitted technical feature
        for feat in data.get("technical_features", []):
            clean_feat = re.sub(r"[^\w\s\-\%]", " ", feat).strip()
            feat_query = f"{ingr_str} {clean_feat}".strip()
            if feat_query and feat_query not in queries:
                queries.append(feat_query)

        return queries

    def retrieve_evidence_for_queries(self, queries: list[str]) -> list[dict[str, Any]]:
        """Retrieves and deduplicates candidates across all queries.

        Uses (collection, chunk_id) tuples for strict deduplication and fair
        round-robin selection so feature-specific evidence is not discarded by global queries.
        """
        per_query_results: list[list[dict[str, Any]]] = []
        for q in queries:
            results = retrieve_multi(
                query=q,
                collection_names=self.collections,
                top_k=min(self.top_k, 3)
            )
            per_query_results.append(results)

        seen_keys: set[tuple[str, str]] = set()
        aggregated_evidence: list[dict[str, Any]] = []

        # Fair round-robin across queries: take rank 0 from each, then rank 1, etc.
        max_depth = max((len(r) for r in per_query_results), default=0)
        for depth in range(max_depth):
            for r_list in per_query_results:
                if depth < len(r_list):
                    item = r_list[depth]
                    col = str(item.get("collection") or "")
                    cid = str(item.get("id") or item.get("chunk_id") or "")
                    key = (col, cid)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        aggregated_evidence.append(item)

        # Retain up to 12 passages so both broad and feature-specific evidence are preserved
        return aggregated_evidence[:12]

    def analyze(self, innovation: dict[str, Any]) -> dict[str, Any]:
        """Runs the complete end-to-end innovation analysis workflow."""
        # 1. Validate & normalize input (raises ValueError if required fields missing)
        norm_data = self._normalize_input(innovation)

        # 2. Generate multi-angle search queries
        queries = self.generate_search_queries(norm_data)

        # 3. Multi-collection retrieval
        retrieved_evidence = self.retrieve_evidence_for_queries(queries)

        # 4. Handle Empty Retrieval Honestly without Hallucinating Findings
        if not retrieved_evidence:
            logger.warning("No evidence retrieved for innovation queries: %s", queries)
            report_markdown = (
                f"### 1. Executive Summary\n"
                f"No documentary evidence or prior-art records were retrieved from the searched pilot knowledge base "
                f"({', '.join(self.collections)}) for the submitted queries.\n\n"
                f"Because no empirical prior-art evidence was retrieved, **no affirmative prior-art assertions or feature comparisons can be made**.\n\n"
                f"### 2. Feature-by-Feature Prior-Art Comparison Table\n"
                f"| Submitted Technical Feature | Status in Searched Pilot Corpus | Detailed Comparison (Ingredient vs. Formulation/Method) | Supporting Passage & Citation |\n"
                f"|---|---|---|---|\n"
            )
            for feat in norm_data["technical_features"]:
                report_markdown += f"| {feat} | NOT_FOUND_IN_CORPUS | No matching disclosure located in the searched pilot corpus. | [Searched Pilot Corpus, N/A, body, N/A] |\n"

            report_markdown += (
                f"\n### 3. Traditional Knowledge Analysis (Section 3(p) Considerations)\n"
                f"No matching traditional knowledge records were retrieved from the pilot database for the submitted ingredients.\n\n"
                f"### 4. Technical Formulation & Synergism Analysis (Section 3(e) Considerations)\n"
                f"No formulation prior art was retrieved from the pilot index. "
                f"Under Section 3(e) of the Indian Patents Act, any synergistic claims must be experimentally substantiated with comparative data.\n\n"
                f"### 5. Research Gaps & Development Recommendations\n"
                f"1. **Broaden Search Coverage:** The pilot database is restricted to the current indexed dataset. Search comprehensive external databases (TKDL, InPASS, WIPO Patentscope).\n"
                f"2. **Validate Efficacy:** Conduct controlled empirical assays demonstrating non-obvious therapeutic benefit.\n\n"
                f"### 6. Search Limitations & Legal Disclaimer\n"
                f"This preliminary assessment reflects **ONLY** the absence of matching records in the searched pilot corpus ({', '.join(self.collections)}). "
                f"Absence of evidence in this pilot database does not legally establish patent novelty, inventive step, or patentability under the Indian Patents Act."
            )
            return {
                "innovation": norm_data,
                "uploaded_documents": norm_data.get("uploaded_documents", []),
                "queries_executed": queries,
                "retrieval_status": "ZERO_RETRIEVAL",
                "sources_count": 0,
                "sources": [],
                "citation_audit": {
                    "citation_format": "source, page, section, chunk_id",
                    "audit_type": "citation_id_validation_only",
                    "semantic_support_verified": False,
                    "verification_disclaimer": "Verifies that cited chunk IDs exist in retrieved documents. Does NOT prove semantic factual truth, patentability, or legal validity.",
                    "total_retrieved_chunks": 0,
                    "total_citations_found": 0,
                    "valid_citations": [],
                    "invalid_citations": [],
                    "has_citations": False,
                    "missing_citations": False,
                    "all_citations_valid": True,
                    "status": "NO_EVIDENCE_AVAILABLE",
                    "status_description": "No evidence chunks were retrieved from knowledge base."
                },
                "report_markdown": report_markdown
            }

        # Format evidence blocks for prompt
        evidence_text_blocks = []
        for i, item in enumerate(retrieved_evidence, 1):
            source = item.get("source", "Unknown")
            doc_type = item.get("document_type", "reference")
            page = item.get("page", "N/A")
            sec = item.get("section", "body")
            cid = item.get("id", f"chunk_{i}")
            text = item.get("text", "")
            evidence_text_blocks.append(
                f"[DOCUMENT {i}]\n"
                f"Source: {source}\n"
                f"Type: {doc_type}\n"
                f"Page: {page} | Section: {sec} | ID: {cid}\n"
                f"Text:\n{text}\n"
            )

        evidence_str = "\n".join(evidence_text_blocks)

        # 5. Construct LLM analysis prompt with clear distinction between user claims & external evidence
        applicant_docs_prompt = ""
        if norm_data.get("uploaded_documents") or norm_data.get("document_text"):
            doc_lines = []
            for d in norm_data.get("uploaded_documents", []):
                fname = d.get("filename", "Uploaded Document")
                pcount = d.get("page_count", 1)
                text_snippet = d.get("extracted_text", "").strip()
                if len(text_snippet) > 2500:
                    text_snippet = text_snippet[:2500] + "... [applicant text truncated for prompt]"
                doc_lines.append(f"- Attached Document: {fname} ({pcount} page(s))\n  Extracted Content (Applicant Submission):\n\"\"\"\n{text_snippet}\n\"\"\"")
            if norm_data.get("document_text"):
                doc_lines.append(f"- Additional Applicant Specification Notes:\n\"\"\"\n{norm_data['document_text'][:2500]}\n\"\"\"")

            applicant_docs_prompt = (
                "\n- Attached Applicant Documentation (UNVERIFIED APPLICANT SUBMISSION - NOT PRIOR ART):\n"
                + "\n".join(doc_lines)
                + "\nCRITICAL: The attached documentation is the applicant's private, unverified submission. "
                "Use it strictly to understand the applicant's claimed formulation, composition, and methodology. "
                "DO NOT treat the applicant's own disclosures as prior art against their innovation, and NEVER cite the applicant's document as external prior-art evidence in the comparison table.\n"
            )

        prompt = f"""Conduct an objective prior-art and technical feature comparison for the following AYUSH innovation.

================================================================================
SECTION A: USER-SUBMITTED INNOVATION SPECIFICATION (Unverified Applicant Claims)
================================================================================
- Title: {norm_data['title']}
- AYUSH System: {norm_data['ayush_system']}
- Technical Problem: {norm_data['problem']}
- Proposed Solution: {norm_data['solution']}
- Ingredients: {', '.join(norm_data['ingredients'])}
- Technical Features (Evaluate EVERY feature separately):
{chr(10).join(f'  {idx}. {f}' for idx, f in enumerate(norm_data['technical_features'], 1))}
- Claimed Advantages: {norm_data['claimed_advantages']}{applicant_docs_prompt}

================================================================================
SECTION B: EXTERNALLY RETRIEVED PRIOR-ART EVIDENCE (Verified Pilot Knowledge Base)
================================================================================
{evidence_str}

================================================================================
REQUIRED ANALYSIS FORMAT & INSTRUCTIONS
================================================================================
Produce a rigorous Markdown report with the following exact sections:

### 1. Executive Summary
A concise 2-paragraph synthesis comparing the proposed innovation to the retrieved prior-art corpus.
- Explicitly state whether the active botanical ingredients are known in classical texts or prior literature.
- Distinguish the applicant's subjective claims from externally verified empirical evidence.

### 2. Feature-by-Feature Prior-Art Comparison Table
Evaluate EVERY submitted technical feature individually. Present a markdown table with columns:
| Submitted Technical Feature | Status in Searched Pilot Corpus (KNOWN_IN_PRIOR_ART / PARTIAL_OVERLAP / NOT_FOUND_IN_CORPUS) | Detailed Comparison (Distinguish Ingredient match vs. Formulation/Method match) | Supporting Passage Quote & Citation [source, page, section, chunk_id] |

Rules for Table:
- KNOWN_IN_PRIOR_ART: The specific technical feature or formulation parameter is explicitly disclosed in the retrieved evidence.
- PARTIAL_OVERLAP: The base herb/compound is documented, but the specific delivery form, matrix, excipient, or method is not disclosed. Clearly explain this distinction.
- NOT_FOUND_IN_CORPUS: No disclosure found in the searched pilot corpus ({', '.join(self.collections)}). Explicitly state that this applies only to the searched pilot database.
- Supporting Passage: Quote the relevant sentence or snippet and provide the exact 4-field citation [source, page, section, chunk_id]. If not found, cite [Searched Pilot Corpus, N/A, body, N/A].

### 3. Traditional Knowledge Analysis (Section 3(p) Considerations)
Analyze whether the active botanical components and their indications are documented in traditional texts (e.g. AFI, API, IMPPAT). Highlight applicability of Section 3(p) of the Indian Patents Act.

### 4. Technical Formulation & Synergism Analysis (Section 3(e) Considerations)
Analyze whether the combination represents a mere admixture or a technical advancement. Highlight whether experimental evidence of synergism (beyond mere additive effects) is required under Section 3(e).

### 5. Research Gaps & Development Recommendations
Provide 3-4 actionable technical research gaps (e.g., stability, pharmacokinetic data, standardization parameters) that the inventor must address.

### 6. Search Limitations & Legal Disclaimer
Explicitly state that this report is generated from a pilot index ({', '.join(self.collections)}) and is NOT an official legal patentability opinion.
"""

        # 6. Generate grounded response
        logger.info("Generating innovation analysis report with model...")
        report_markdown = generate_response(self.model, self.system_prompt, prompt)

        # 7. Validate Citations
        citation_audit = self._rag_validator.validate_citations(report_markdown, retrieved_evidence)
        if citation_audit.get("invalid_citations"):
            logger.warning("Unverified citation IDs in innovation report: %s", citation_audit["invalid_citations"])
            warning_notice = (
                f"\n\n> ⚠️ **Citation Audit Alert:** The report cites unverified document ID(s): "
                f"`{', '.join(citation_audit['invalid_citations'])}`. These citations do not exist in the retrieved evidence."
            )
            report_markdown += warning_notice

        # 8. Structure Sources for Return & Frontend Display (including actual retrieved passage text)
        formatted_sources = []
        for item in retrieved_evidence:
            formatted_sources.append({
                "source": item.get("source"),
                "document_type": item.get("document_type"),
                "page": item.get("page"),
                "section": item.get("section"),
                "id": item.get("id"),
                "collection": item.get("collection"),
                "text": item.get("text", ""),
                "evidence": item.get("text", "")
            })

        return {
            "innovation": norm_data,
            "uploaded_documents": norm_data.get("uploaded_documents", []),
            "queries_executed": queries,
            "retrieval_status": "NONEMPTY_RETRIEVAL",
            "sources_count": len(retrieved_evidence),
            "sources": formatted_sources,
            "citation_audit": citation_audit,
            "report_markdown": report_markdown
        }
