"""IP-SAKTI Sahayak — Demonstration Web Interface.

Provides a 4-section Streamlit application:
1. 🏠 Home — Platform overview, corpus statistics, mission, and disclaimers.
2. 💡 Innovation Submission — Structured submission of AYUSH formulations with 1-click sample loader.
3. 📊 Analysis Results — Feature-by-feature prior-art comparison, Section 3(p)/3(e) analysis, and evidence inspector.
4. 💬 Patent Assistant — Multi-turn conversational RAG with intent routing, pronoun resolution, and genuine citations.
"""
from __future__ import annotations
import json
import logging
import time
from typing import Any

import streamlit as st

from assistant_engine import PatentAssistantEngine
from config import COLLECTION_NAME, EMBEDDING_MODEL, GEMINI_MODEL, VECTOR_STORE_DIR
from innovation_engine import InnovationAnalysisEngine
from vector_store import get_or_create_collection

# Page setup
st.set_page_config(
    page_title="IP-SAKTI Sahayak | AYUSH Prior-Art Discovery",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished government/scientific look
st.markdown("""
<style>
    .report-title {
        color: #1b4d3e;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #1b4d3e;
    }
    .source-box {
        font-size: 0.88rem;
        background-color: #f1f5f9;
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Engines:
# 1. Patent Assistant is session-isolated to prevent sharing conversation history across users
def get_patent_assistant() -> PatentAssistantEngine:
    if "patent_assistant" not in st.session_state:
        st.session_state["patent_assistant"] = PatentAssistantEngine(top_k=4)
    return st.session_state["patent_assistant"]


# 2. Innovation Engine stored per session without global cache interference
def get_innovation_engine() -> InnovationAnalysisEngine:
    if "innovation_engine" not in st.session_state:
        st.session_state["innovation_engine"] = InnovationAnalysisEngine(top_k=3)
    return st.session_state["innovation_engine"]


# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "🏠 Home"


# Sidebar Navigation & Statistics
st.sidebar.title("🌿 IP-SAKTI Sahayak")
st.sidebar.caption("AYUSH Prior-Art Discovery & Patent Research")

# Navigation radio
nav_selection = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "💡 Innovation Submission", "📊 Analysis Results", "💬 Patent Assistant"],
    index=["🏠 Home", "💡 Innovation Submission", "📊 Analysis Results", "💬 Patent Assistant"].index(st.session_state["nav_page"])
)

# Keep navigation state synchronized
if nav_selection != st.session_state["nav_page"]:
    st.session_state["nav_page"] = nav_selection
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Knowledge Base Status")

try:
    ayush_col = get_or_create_collection("ip_sakti_ayush_v1")
    curcuma_col = get_or_create_collection("ip_sakti_curcuma_test_v1")
    c1_count = ayush_col.count()
    c2_count = curcuma_col.count()
    total_records = c1_count + c2_count

    st.sidebar.metric("Total Indexed Evidence", f"{total_records:,}")
    with st.sidebar.expander("Collection Breakdown", expanded=False):
        st.write(f"• **Patent & Legal Corpus:** {c1_count:,} chunks")
        st.write(f"• **IMPPAT Turmeric Dataset:** {c2_count:,} records")
        st.caption("Embedding: intfloat/multilingual-e5-base")
        st.caption(f"LLM: {GEMINI_MODEL}")
except Exception as e:
    st.sidebar.error(f"Vector Store Connection: {e}")

st.sidebar.markdown("---")
st.sidebar.info(
    "**Pre-Patent Research Prototype**\n\n"
    "Semantic similarity and database retrieval assist prior-art discovery, "
    "but do not determine formal legal patentability or validity under the Indian Patents Act."
)

if st.sidebar.button("Reset Demonstration State", use_container_width=True):
    st.session_state["chat_history"] = []
    st.session_state["analysis_result"] = None
    st.session_state["patent_assistant"] = PatentAssistantEngine(top_k=4)
    st.success("Session reset.")
    st.rerun()


# ==============================================================================
# SECTION 1: HOME
# ==============================================================================
if st.session_state["nav_page"] == "🏠 Home":
    st.markdown('<h1 class="report-title">🌿 IP-SAKTI Sahayak</h1>', unsafe_allow_html=True)
    st.subheader("AI-Powered AYUSH Prior-Art Discovery & Patent Research Assistant")

    st.markdown("""
    **IP-SAKTI Sahayak** is designed for inventors, researchers, and patent analysts in the **AYUSH** 
    (Ayurveda, Yoga & Naturopathy, Unani, Siddha, and Homeopathy) sector. It bridges ancient classical formulations, 
    scientific phytochemistry records, and contemporary patent disclosures to accelerate rigorous prior-art discovery.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 💡 Innovation Analysis Engine
        - **Feature-Level Structuring:** Deconstructs complex polyherbal formulations into botanical entities, excipients, and technical mechanisms.
        - **Multi-Collection Retrieval:** Simultaneously scans traditional Ayurvedic texts, scientific bioactivity databases (IMPPAT), and patent claims.
        - **Statutory Prior-Art Check:** Assesses disclosures against **Section 3(p)** (Traditional Knowledge) and **Section 3(e)** (Mere Admixture / Synergism requirement) of the Indian Patents Act.
        """)
        if st.button("Submit an Innovation for Analysis →", type="primary"):
            st.session_state["nav_page"] = "💡 Innovation Submission"
            st.rerun()

    with col2:
        st.markdown("""
        ### 💬 Conversational Patent Assistant
        - **Multi-Turn Research Dialogue:** Handles follow-up questions with automatic pronoun resolution and topic tracking.
        - **Multi-Collection Hybrid RRF:** Fuses dense semantic search and BM25 keyword matching across multiple ChromaDB collections.
        - **Strict Evidence Grounding:** Provides verifiable 4-field citations `[source, page, section, chunk_id]` with zero fabricated facts.
        - **Domain Filtering:** Rejects out-of-domain questions with zero unnecessary vector queries.
        """)
        if st.button("Open Patent Assistant Chat →"):
            st.session_state["nav_page"] = "💬 Patent Assistant"
            st.rerun()

    st.markdown("---")
    st.subheader("Pilot Demonstration Knowledge Corpus")
    c_a, c_b, c_c = st.columns(3)
    c_a.metric("Patent & Legal Corpus", f"{c1_count:,} chunks", "Patents, Claims, Guidelines")
    c_b.metric("IMPPAT Curcuma Dataset", f"{c2_count:,} records", "Phytochemicals & Formulations")
    c_c.metric("Active Model", GEMINI_MODEL, "REST Transport Grounded")

    st.warning(
        "**Legal Disclaimer:** This software provides preliminary prior-art discovery assistance based on its indexed corpus. "
        "It does not constitute legal patent counseling. Absence of evidence in this pilot database does not guarantee patent novelty."
    )


# ==============================================================================
# SECTION 2: INNOVATION SUBMISSION
# ==============================================================================
elif st.session_state["nav_page"] == "💡 Innovation Submission":
    st.markdown('<h1 class="report-title">💡 Innovation Submission</h1>', unsafe_allow_html=True)
    st.caption("Submit an AYUSH formulation or technical composition for automated feature-level prior-art analysis.")

    # 1-Click Demo Loader
    if st.button("📋 Load Example: Turmeric & Piperine Wound Healing Emulgel", help="Click to pre-fill realistic demonstration data"):
        st.session_state["form_title"] = "Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing"
        st.session_state["form_system"] = "Ayurveda"
        st.session_state["form_problem"] = "Poor dermal bioavailability, chemical instability, and rapid degradation of topical curcumin in open wound healing."
        st.session_state["form_solution"] = "A stable topical emulgel incorporating standardized Curcuma longa rhizome extract with piperine in a carbopol polymer matrix."
        st.session_state["form_ingredients"] = "Curcuma longa rhizome extract (95% curcuminoids)\nPiper nigrum extract / Piperine\nCarbopol 940\nTriethanolamine\nPurified Water"
        st.session_state["form_features"] = "Standardized Curcuma longa extract containing 95% total curcuminoids\nPiperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation\nTopical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5\nDemonstrated 2.5-fold acceleration in epithelial wound closure over single herbs"
        st.session_state["form_advantages"] = "Enhanced dermal penetration and synergistic wound healing without systemic toxicity."
        st.success("Example innovation data loaded! Review the fields below and click 'Analyze Innovation'.")

    # Form inputs with strictly explicit keyword arguments (no positional-keyword overlap)
    with st.form("innovation_form"):
        title = st.text_input(
            label="Innovation Title (Required)",
            value=st.session_state.get("form_title", ""),
            placeholder="e.g. Synergistic Topical Emulgel of Curcuma longa..."
        )
        col_sys, col_adv = st.columns([1, 2])
        with col_sys:
            ayush_system = st.selectbox(
                label="AYUSH System",
                options=["Ayurveda", "Siddha", "Unani", "Homeopathy", "General AYUSH"],
                index=["Ayurveda", "Siddha", "Unani", "Homeopathy", "General AYUSH"].index(st.session_state.get("form_system", "Ayurveda"))
            )
        with col_adv:
            claimed_advantages = st.text_input(
                label="Claimed Advantages / Novel Effect (Optional applicant claim)",
                value=st.session_state.get("form_advantages", ""),
                placeholder="e.g. 2.5-fold increase in wound closure rate over single herbs"
            )

        col_p, col_s = st.columns(2)
        with col_p:
            problem = st.text_area(
                label="Technical Problem Addressed (Optional applicant claim)",
                value=st.session_state.get("form_problem", ""),
                height=110,
                placeholder="Describe the medical or technological limitation in existing treatments..."
            )
        with col_s:
            solution = st.text_area(
                label="Proposed Technical Solution (Optional applicant claim)",
                value=st.session_state.get("form_solution", ""),
                height=110,
                placeholder="Describe the composition, method, or technical delivery mechanism..."
            )

        ingredients = st.text_area(
            label="Ingredients / Bioactive Substances (Required — one per line or comma-separated)",
            value=st.session_state.get("form_ingredients", ""),
            height=90,
            placeholder="Curcuma longa rhizome extract\nPiper nigrum extract\nCarbopol 940..."
        )

        technical_features = st.text_area(
            label="Key Technical Features & Formulation Parameters (Required — one per line)",
            value=st.session_state.get("form_features", ""),
            height=120,
            placeholder="• Standardized Curcuma longa extract containing 95% total curcuminoids\n• Piperine bioenhancer at 1:10 w/w ratio\n• Emulgel base at pH 6.0-6.5..."
        )

        submitted = st.form_submit_button("🚀 Analyze Innovation Against Knowledge Base", type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Innovation Title is required.")
        elif not ingredients.strip():
            st.error("At least one ingredient or botanical substance is required.")
        elif not technical_features.strip():
            st.error("At least one key technical feature is required for prior-art comparison.")
        else:
            with st.spinner("Analyzing innovation: generating sub-queries, retrieving evidence, and evaluating prior-art..."):
                try:
                    engine = get_innovation_engine()
                    input_payload = {
                        "title": title,
                        "ayush_system": ayush_system,
                        "problem": problem,
                        "solution": solution,
                        "ingredients": ingredients,
                        "technical_features": technical_features,
                        "claimed_advantages": claimed_advantages
                    }
                    result = engine.analyze(input_payload)
                    st.session_state["analysis_result"] = result
                    st.session_state["nav_page"] = "📊 Analysis Results"
                    st.rerun()
                except ValueError as ve:
                    st.error(f"Input Validation Error: {ve}")
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")


# ==============================================================================
# SECTION 3: ANALYSIS RESULTS
# ==============================================================================
elif st.session_state["nav_page"] == "📊 Analysis Results":
    st.markdown('<h1 class="report-title">📊 Innovation Analysis Results</h1>', unsafe_allow_html=True)

    result = st.session_state.get("analysis_result")
    if not result:
        st.info("No innovation has been analyzed yet in this session.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Go to Innovation Submission"):
                st.session_state["nav_page"] = "💡 Innovation Submission"
                st.rerun()
        with c2:
            if st.button("Run Quick Turmeric Demo Analysis"):
                with st.spinner("Running quick demonstration analysis..."):
                    engine = get_innovation_engine()
                    sample = {
                        "title": "Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing",
                        "ayush_system": "Ayurveda",
                        "problem": "Poor dermal bioavailability, chemical instability, and rapid degradation of topical curcumin in wound healing.",
                        "solution": "A stable topical emulgel incorporating standardized Curcuma longa rhizome extract with piperine in a carbopol polymer matrix.",
                        "ingredients": ["Curcuma longa rhizome extract", "Piper nigrum / Piperine", "Carbopol 940", "Triethanolamine", "Purified Water"],
                        "technical_features": [
                            "Standardized Curcuma longa extract containing 95% total curcuminoids",
                            "Piperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation",
                            "Topical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5",
                            "Demonstrated 2.5-fold acceleration in epithelial wound closure over single herbs"
                        ],
                        "claimed_advantages": "Enhanced dermal penetration and synergistic wound healing without systemic toxicity."
                    }
                    st.session_state["analysis_result"] = engine.analyze(sample)
                    st.rerun()
    else:
        inno = result["innovation"]
        st.subheader(f"Report: {inno['title']}")
        st.caption(f"System: {inno['ayush_system']} | Ingredients: {', '.join(inno['ingredients'])}")

        # Distinguish user claims from verified evidence
        st.info(
            "ℹ️ **Evaluation Framework:** User-submitted specifications (problem, solution, claimed efficacy) "
            "represent **unverified applicant claims**. The feature evaluation below compares these claims "
            "strictly against empirical evidence retrieved from the indexed knowledge base."
        )

        # Metrics bar
        m1, m2, m3 = st.columns(3)
        m1.metric("Sub-Queries Executed", len(result["queries_executed"]))
        m2.metric("Evidence Passages Retrieved", result["sources_count"])
        m3.metric("Multi-Collection Search", "2 Collections Active")

        # Executed queries view
        with st.expander("🔍 Inspect Generated Sub-Queries", expanded=False):
            for i, q in enumerate(result["queries_executed"], 1):
                st.markdown(f"**{i}.** `{q}`")

        # Citation Audit Transparency Display (Differentiating ID matching from semantic truth)
        audit = result.get("citation_audit")
        if audit:
            st.markdown("#### Citation ID Verification")
            status = audit.get("status")
            if status == "ID_MATCH_CONFIRMED":
                st.info(
                    f"✓ **Citation ID Match Confirmed:** All {len(audit.get('valid_citations', []))} cited chunk ID(s) "
                    f"match records in the retrieved evidence set.\n\n"
                    f"*Note: Verifies document reference IDs only; does not certify legal patentability or semantic factual truth.*"
                )
            elif status == "MISSING_CITATIONS":
                st.warning(
                    "⚠️ **Missing Citations Notice:** The report contains factual statements without specific documentary chunk citations."
                )
            elif status == "FABRICATED_OR_UNMATCHED_IDS":
                st.error(
                    f"❌ **Citation Audit Alert:** Unverified citation ID(s) detected: `{audit.get('invalid_citations')}`. "
                    f"These references do not exist in the retrieved evidence."
                )
            elif status == "NO_EVIDENCE_AVAILABLE":
                st.info("ℹ️ **No Evidence Retrieved:** Zero external chunks retrieved; no document citations expected.")

        # Render the complete Markdown Report
        st.markdown("---")
        st.markdown(result["report_markdown"])

        # Single Evidence Inspector with full supporting passage text (No duplicate loop)
        st.markdown("---")
        st.subheader("📚 Retrieved Evidence Passages & Source Audits")
        if not result["sources"]:
            st.info("No external evidence passages were retrieved for this innovation.")
        else:
            for i, s in enumerate(result["sources"], 1):
                page_str = s.get('page') if s.get('page') not in (None, 'N/A') else 'N/A'
                with st.expander(f"Source #{i}: {s['source']} ({s['document_type']}) · Page {page_str} · [{s['collection']}]"):
                    st.write(f"**Document Type:** `{s['document_type']}`")
                    st.write(f"**Section:** `{s['section']}`")
                    st.write(f"**Chunk ID:** `{s['id']}`")
                    st.write(f"**Collection:** `{s['collection']}`")
                    st.markdown("**Retrieved Supporting Passage Text:**")
                    passage = s.get("text") or s.get("evidence") or "Passage text unavailable"
                    st.caption(f"> {passage}")

        st.download_button(
            "📥 Download Analysis Report (Markdown)",
            data=result["report_markdown"],
            file_name=f"IP_SAKTI_Report_{inno['title'][:20].replace(' ', '_')}.md",
            mime="text/markdown"
        )


# ==============================================================================
# SECTION 4: PATENT ASSISTANT
# ==============================================================================
elif st.session_state["nav_page"] == "💬 Patent Assistant":
    st.markdown('<h1 class="report-title">💬 Conversational Patent Assistant</h1>', unsafe_allow_html=True)
    st.caption("Ask questions about AYUSH plants, formulations, patent claims, and Indian patent law guidelines.")

    # Demonstration Prompt Shortcuts
    st.markdown("**Sample demonstration queries (click to populate):**")
    p_cols = st.columns(4)
    if p_cols[0].button("🌿 Turmeric Phytochemicals", use_container_width=True):
        st.session_state["suggested_prompt"] = "What phytochemicals and bioactivities are reported for Curcuma longa?"
    if p_cols[1].button("🧴 Skin Formulations", use_container_width=True):
        st.session_state["suggested_prompt"] = "Which Ayurvedic formulations contain Curcuma longa for skin disorders?"
    if p_cols[2].button("⚖️ Patent Synergism 3(e)", use_container_width=True):
        st.session_state["suggested_prompt"] = "What are the patent examination requirements for herbal admixtures under Section 3(e)?"
    if p_cols[3].button("🚫 Out-of-Domain Test", use_container_width=True):
        st.session_state["suggested_prompt"] = "What is the capital of France?"

    st.markdown("---")

    # Render Chat History (Single rendering loop for all turns, with supporting passages)
    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander(f"📚 Retrieved Sources & Supporting Passages ({len(message['sources'])} records)", expanded=False):
                    for src in message["sources"]:
                        st.markdown(
                            f"- **{src.get('source')}** | *{src.get('document_type')}* | "
                            f"Page: {src.get('page', 'N/A')} | Sec: {src.get('section', 'N/A')} | "
                            f"`{src.get('id')}`"
                        )
                        passage = src.get("text") or src.get("evidence")
                        if passage:
                            st.caption(f"> {passage[:280]}..." if len(passage) > 280 else f"> {passage}")

    # Chat Input
    suggested = st.session_state.pop("suggested_prompt", None)
    user_input = st.chat_input("Enter your AYUSH research or patent question...")

    query_to_process = suggested if suggested else user_input

    if query_to_process:
        # Append User Message to conversation history
        st.session_state["chat_history"].append({"role": "user", "content": query_to_process})

        # Generate Assistant Response through session-isolated engine
        engine = get_patent_assistant()
        with st.spinner("Searching multi-collection knowledge base & verifying evidence..."):
            response = engine.ask(query_to_process)
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": response["answer"],
                "sources": response.get("sources", []),
                "category": response.get("category")
            })

        # Trigger single clean rerun so history renders with exactly one source expander
        st.rerun()
