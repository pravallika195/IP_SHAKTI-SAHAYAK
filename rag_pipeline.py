
import logging
import re

from retriever import retrieve
from prompt_builder import build_prompt, get_system_prompt
from llm_config import configure_llm, generate_response
from config import TOP_K

logger = logging.getLogger(__name__)


class RAGPipeline:

    def __init__(self, top_k: int = TOP_K, model=None):
        self.top_k = top_k
        self.system_prompt = get_system_prompt()
        self.model = model or configure_llm(self.system_prompt)

    @staticmethod
    def validate_citations(answer: str, chunks: list) -> dict:
        """
        Check whether citation chunk IDs in the generated answer
        exist in the retrieved evidence.
        
        Expected citation format:
        [source, page, section, chunk_id]
        """

        retrieved_ids = {
            str(chunk.get("chunk_id") or chunk.get("id"))
            for chunk in chunks
            if chunk.get("chunk_id") or chunk.get("id")
        }

        citation_pattern = r"\[([^\[\]]+)\]"
        citation_blocks = re.findall(citation_pattern, answer)

        cited_ids = []
        invalid_ids = []

        for block in citation_blocks:
            parts = block.rsplit(",", 3)
            if len(parts) != 4:
                continue

            chunk_id_raw = parts[-1].strip()

            candidate_ids = [c.strip() for c in chunk_id_raw.split(";") if c.strip()]

            for chunk_id in candidate_ids:
                if chunk_id in retrieved_ids:
                    cited_ids.append(chunk_id)
                elif chunk_id.upper() in {"N/A", "NONE", "UNAVAILABLE"}:
                    
                    continue
                else:
                    invalid_ids.append(chunk_id)

        cited_ids = list(dict.fromkeys(cited_ids))
        invalid_ids = list(dict.fromkeys(invalid_ids))

        has_citations = len(cited_ids) > 0
        has_invalid = len(invalid_ids) > 0
        missing_citations = (not has_citations) and (len(retrieved_ids) > 0)

        if not retrieved_ids:
            status = "NO_EVIDENCE_AVAILABLE"
            status_desc = "No external evidence chunks were retrieved; no citations expected."
        elif has_invalid:
            status = "FABRICATED_OR_UNMATCHED_IDS"
            status_desc = f"Found {len(invalid_ids)} citation ID(s) not present in retrieved evidence: {invalid_ids}"
        elif missing_citations:
            status = "MISSING_CITATIONS"
            status_desc = "Response lacks document citations despite evidence being available."
        else:
            status = "ID_MATCH_CONFIRMED"
            status_desc = "All cited chunk IDs correspond to retrieved knowledge base records."

        return {
            "citation_format": "source, page, section, chunk_id",
            "audit_type": "citation_id_validation_only",
            "semantic_support_verified": False,
            "verification_disclaimer": "Verifies that cited chunk IDs exist in retrieved documents. Does NOT prove semantic factual truth, patentability, or legal validity.",
            "total_retrieved_chunks": len(retrieved_ids),
            "total_citations_found": len(cited_ids) + len(invalid_ids),
            "valid_citations": cited_ids,
            "invalid_citations": invalid_ids,
            "has_citations": has_citations,
            "missing_citations": missing_citations,
            "all_citations_valid": (not has_invalid) and has_citations,
            "status": status,
            "status_description": status_desc,
        }

    def run(
        self,
        query: str,
        user_language: str = "English",
        filters: dict | None = None
    ) -> dict:

        if not query or not query.strip():
            raise ValueError(
                "Enter a formulation, ingredient combination "
                "or prior-art question."
            )

        chunks = retrieve(
            query,
            top_k=self.top_k,
            filters=filters
        )

        if not chunks:
            return {
                "answer": (
                    "No relevant documents were retrieved from "
                    "the current knowledge base. Check that "
                    "documents have been ingested and try a "
                    "more specific query."
                ),
                "sources": [],
                "retrieved_count": 0,
                "citation_audit": None
            }

        prompt = build_prompt(
            query,
            chunks,
            user_language=user_language
        )

        answer = generate_response(
            self.model,
            self.system_prompt,
            prompt
        )

        citation_audit = self.validate_citations(
            answer,
            chunks
        )

        sources = []

        for item in chunks:
            sources.append({
                "id": item.get("id"),
                "chunk_id": item.get("chunk_id"),
                "source": item.get("source"),
                "publication_number": item.get("publication_number"),
                "priority_date": item.get("priority_date"),
                "publication_date": item.get("publication_date"),
                "page": item.get("page"),
                "section": item.get("section"),
                "language": item.get("language"),
                "document_type": item.get("document_type"),
                "rrf_score": item.get("rrf_score"),
                "evidence": item.get("text", "")
            })

        if not citation_audit["all_citations_valid"]:
            logger.warning(
                "Invalid citations detected: %s",
                citation_audit["invalid_citations"]
            )

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_count": len(chunks),
            "citation_audit": citation_audit
        }

validate_citations = RAGPipeline.validate_citations

