"""Comprehensive verification suite for Phase 1 - Flask API Gateway Adaptation.

Tests:
1. Endpoint 1: GET /health (Preserved health diagnostics)
2. Endpoint 2: GET /api/collections/status (Multi-collection availability and exact counts)
3. Endpoint 3: POST /api/query (Preserved single-turn RAG query & error handling)
4. Endpoint 4: POST /api/assistant/chat:
   - Request body validation (session_id, query)
   - Greeting & Out-of-Domain intent routing
   - Two-turn conversation context retention
   - Context isolation across two separate sessions
5. Endpoint 5: POST /api/assistant/reset (Session context wipe)
6. Endpoint 6: POST /api/innovation/analyze:
   - Input validation (missing title, ingredients, features)
   - Full prior-art analysis report generation
7. CORS Headers verification (GET/POST and OPTIONS preflight)
8. ChromaDB collection preservation check (counts unchanged before and after)
"""
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import app
from vector_store import get_client


def run_gateway_tests():
    print("=" * 80)
    print("STARTING FLASK API GATEWAY (PHASE 1) VERIFICATION SUITE")
    print("=" * 80)

    client = app.test_client()
    chroma_client = get_client()

    # --------------------------------------------------------------------------
    # Initial Baseline Collection Check
    # --------------------------------------------------------------------------
    initial_ayush_count = chroma_client.get_collection("ip_sakti_ayush_v1").count()
    initial_curcuma_count = chroma_client.get_collection("ip_sakti_curcuma_test_v1").count()
    print(f"\n[Baseline Verification] Existing ChromaDB Collections:")
    print(f"  - ip_sakti_ayush_v1: {initial_ayush_count} chunks")
    print(f"  - ip_sakti_curcuma_test_v1: {initial_curcuma_count} chunks")
    assert initial_ayush_count == 2150, f"Expected 2150 chunks, got {initial_ayush_count}"
    assert initial_curcuma_count == 1297, f"Expected 1297 chunks, got {initial_curcuma_count}"

    # --------------------------------------------------------------------------
    # TEST 1: GET /health
    # --------------------------------------------------------------------------
    print("\n--- TEST 1: GET /health ---")
    res = client.get("/health")
    print(f"Status: {res.status_code}, Body: {res.get_json()}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["collection"] == "ip_sakti_ayush_v1"
    assert data["chunks"] == 2150
    assert res.headers.get("Access-Control-Allow-Origin") in {"*", "http://localhost:5173"}
    print(">>> TEST 1 PASSED: /health operational with CORS.")

    # --------------------------------------------------------------------------
    # TEST 2: GET /api/collections/status
    # --------------------------------------------------------------------------
    print("\n--- TEST 2: GET /api/collections/status ---")
    res = client.get("/api/collections/status")
    print(f"Status: {res.status_code}, Body: {json.dumps(res.get_json(), indent=2)}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["total_chunks"] == 3447
    assert data["collections"]["ip_sakti_ayush_v1"]["count"] == 2150
    assert data["collections"]["ip_sakti_ayush_v1"]["available"] is True
    assert data["collections"]["ip_sakti_curcuma_test_v1"]["count"] == 1297
    assert data["collections"]["ip_sakti_curcuma_test_v1"]["available"] is True
    print(">>> TEST 2 PASSED: Both collections verified and accurately reported.")

    # --------------------------------------------------------------------------
    # TEST 3: POST /api/query (Preserved RAG Endpoint)
    # --------------------------------------------------------------------------
    print("\n--- TEST 3: POST /api/query ---")
    # 3a. Invalid (empty query)
    res_bad = client.post("/api/query", json={"query": ""})
    assert res_bad.status_code == 400
    print(f"  [x] Empty query rejected: {res_bad.get_json()}")

    # 3b. Invalid language
    res_lang = client.post("/api/query", json={"query": "turmeric", "language": "German"})
    assert res_lang.status_code == 400
    print(f"  [x] Invalid language rejected: {res_lang.get_json()}")

    # 3c. Valid query
    print("  Executing valid query to preserved /api/query...")
    res_valid = client.post("/api/query", json={
        "query": "What are the therapeutic uses of Curcuma longa?",
        "language": "English"
    })
    assert res_valid.status_code == 200
    q_data = res_valid.get_json()
    assert "answer" in q_data
    assert "sources" in q_data
    assert "citation_audit" in q_data
    print(f"  [x] Preserved /api/query answered with {len(q_data['sources'])} sources.")
    print(">>> TEST 3 PASSED: Preserved /api/query behavior confirmed.")

    # --------------------------------------------------------------------------
    # TEST 4: POST /api/assistant/chat (Validation, Intents, Context Retention, Isolation)
    # --------------------------------------------------------------------------
    print("\n--- TEST 4: POST /api/assistant/chat ---")
    # 4a. Missing session_id
    res_no_session = client.post("/api/assistant/chat", json={"query": "Hello"})
    assert res_no_session.status_code == 400
    assert "session_id is required" in res_no_session.get_json()["error"]
    print(f"  [x] Missing session_id caught correctly: {res_no_session.get_json()}")

    # 4b. Missing query
    res_no_query = client.post("/api/assistant/chat", json={"session_id": "sess_1", "query": ""})
    assert res_no_query.status_code == 400
    assert "query is required" in res_no_query.get_json()["error"]
    print(f"  [x] Missing query caught correctly: {res_no_query.get_json()}")

    # 4c. Greeting intent
    res_greet = client.post("/api/assistant/chat", json={
        "session_id": "sess_user_alpha",
        "query": "Hello, what can you do?"
    })
    assert res_greet.status_code == 200
    greet_json = res_greet.get_json()
    assert greet_json["category"] == "GREETING"
    assert len(greet_json["sources"]) == 0
    print(f"  [x] Greeting routed without vector search: Category={greet_json['category']}")

    # 4d. Out-of-domain intent
    res_ood = client.post("/api/assistant/chat", json={
        "session_id": "sess_user_alpha",
        "query": "What is the capital of France?"
    })
    assert res_ood.status_code == 200
    ood_json = res_ood.get_json()
    assert ood_json["category"] == "OUT_OF_DOMAIN"
    assert len(ood_json["sources"]) == 0
    print(f"  [x] Out-of-domain routed without vector search: Category={ood_json['category']}")

    # 4e. Two-Turn Follow-Up Conversation in Session Alpha
    print("  Executing Session Alpha - Turn 1: 'What phytochemicals are reported for Curcuma longa?'")
    res_t1 = client.post("/api/assistant/chat", json={
        "session_id": "sess_user_alpha",
        "query": "What phytochemicals are reported for Curcuma longa?"
    })
    assert res_t1.status_code == 200
    t1_data = res_t1.get_json()
    assert t1_data["category"] in {"AYUSH_RESEARCH", "FOLLOW_UP"}
    assert len(t1_data["sources"]) > 0
    print(f"  [x] Turn 1 complete: Category={t1_data['category']}, Sources={len(t1_data['sources'])}")

    print("  Executing Session Alpha - Turn 2: 'Which Ayurvedic formulations contain it for skin disorders?'")
    res_t2 = client.post("/api/assistant/chat", json={
        "session_id": "sess_user_alpha",
        "query": "Which Ayurvedic formulations contain it for skin disorders?"
    })
    assert res_t2.status_code == 200
    t2_data = res_t2.get_json()
    assert t2_data["category"] == "FOLLOW_UP"
    resolved = (t2_data.get("resolved_query") or t2_data.get("standalone_query") or "").lower()
    print(f"  [x] Turn 2 Resolved Query: '{resolved}'")
    assert " it " not in f" {resolved} ", f"Pronoun 'it' was not resolved in: {resolved}"
    print(f"  [x] Turn 2 coreference resolved using conversation history.")

    # 4f. Two-Session Isolation Test (Session Beta has ZERO context from Session Alpha)
    print("  Executing Session Beta - Ambiguous pronoun query: 'Which formulations contain it?'")
    res_beta = client.post("/api/assistant/chat", json={
        "session_id": "sess_user_beta",
        "query": "Which formulations contain it?"
    })
    assert res_beta.status_code == 200
    beta_data = res_beta.get_json()
    beta_resolved = (beta_data.get("resolved_query") or beta_data.get("standalone_query") or "").lower()
    print(f"  [x] Session Beta Resolved Query: '{beta_resolved}'")
    assert "curcuma" not in beta_resolved, (
        f"Data leakage detected! Session Beta referenced Session Alpha's entity: {beta_resolved}"
    )
    print("  [x] Session Beta did NOT leak context from Session Alpha.")
    print(">>> TEST 4 PASSED: Patent Assistant chat, context retention, and session isolation verified.")

    # --------------------------------------------------------------------------
    # TEST 5: POST /api/assistant/reset
    # --------------------------------------------------------------------------
    print("\n--- TEST 5: POST /api/assistant/reset ---")
    # 5a. Missing session_id
    res_reset_bad = client.post("/api/assistant/reset", json={})
    assert res_reset_bad.status_code == 400
    print(f"  [x] Reset rejected without session_id: {res_reset_bad.get_json()}")

    # 5b. Valid reset
    res_reset = client.post("/api/assistant/reset", json={"session_id": "sess_user_alpha"})
    assert res_reset.status_code == 200
    assert res_reset.get_json()["status"] == "ok"
    print(f"  [x] Session Alpha reset confirmed: {res_reset.get_json()}")
    print(">>> TEST 5 PASSED: Session reset operational.")

    # --------------------------------------------------------------------------
    # TEST 6: POST /api/innovation/analyze (Validation & Analysis)
    # --------------------------------------------------------------------------
    print("\n--- TEST 6: POST /api/innovation/analyze ---")
    # 6a. Missing title
    res_inv_title = client.post("/api/innovation/analyze", json={
        "title": "",
        "ingredients": ["Curcuma longa"],
        "technical_features": ["95% curcuminoids"]
    })
    assert res_inv_title.status_code == 400
    print(f"  [x] Missing title caught: {res_inv_title.get_json()}")

    # 6b. Missing ingredients
    res_inv_ingr = client.post("/api/innovation/analyze", json={
        "title": "Bio-Curcumin Emulgel",
        "ingredients": [],
        "technical_features": ["95% curcuminoids"]
    })
    assert res_inv_ingr.status_code == 400
    print(f"  [x] Missing ingredients caught: {res_inv_ingr.get_json()}")

    # 6c. Missing technical_features
    res_inv_feat = client.post("/api/innovation/analyze", json={
        "title": "Bio-Curcumin Emulgel",
        "ingredients": ["Curcuma longa"],
        "technical_features": []
    })
    assert res_inv_feat.status_code == 400
    print(f"  [x] Missing technical_features caught: {res_inv_feat.get_json()}")

    # 6d. Valid Full Innovation Analysis Run
    print("  Executing valid innovation analysis...")
    sample_payload = {
        "title": "Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing",
        "ayush_system": "Ayurveda",
        "problem": "Poor dermal bioavailability, chemical instability, and rapid degradation of topical curcumin.",
        "solution": "A stable topical emulgel incorporating standardized Curcuma longa rhizome extract with piperine in a carbopol polymer matrix.",
        "ingredients": [
            "Curcuma longa rhizome extract",
            "Piper nigrum / Piperine",
            "Carbopol 940",
            "Triethanolamine",
            "Purified Water"
        ],
        "technical_features": [
            "Standardized Curcuma longa extract containing 95% total curcuminoids",
            "Piperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation",
            "Topical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5",
            "Demonstrated 2.5-fold acceleration in epithelial wound closure over single herbs"
        ],
        "claimed_advantages": "Enhanced dermal penetration and synergistic wound healing without systemic toxicity."
    }
    res_analysis = client.post("/api/innovation/analyze", json=sample_payload)
    assert res_analysis.status_code == 200
    an_data = res_analysis.get_json()
    assert "report_markdown" in an_data
    assert "sources" in an_data
    assert "queries_executed" in an_data
    assert "retrieval_status" in an_data
    assert "citation_audit" in an_data
    assert len(an_data["queries_executed"]) >= 6
    assert len(an_data["sources"]) > 0
    print(f"  [x] Innovation analysis completed:")
    print(f"      - Retrieval Status: {an_data['retrieval_status']}")
    print(f"      - Queries Executed: {len(an_data['queries_executed'])}")
    print(f"      - Evidence Sources Retrieved: {len(an_data['sources'])}")
    print(f"      - Citation Audit Status: {an_data['citation_audit']['status']}")
    print(">>> TEST 6 PASSED: Innovation analysis endpoint validated and operational.")

    # --------------------------------------------------------------------------
    # TEST 7: CORS Preflight & Header Verification
    # --------------------------------------------------------------------------
    print("\n--- TEST 7: CORS Preflight & Header Verification ---")
    opt_res = client.options("/api/assistant/chat")
    assert opt_res.status_code == 200
    assert opt_res.headers.get("Access-Control-Allow-Origin") in {"*", "http://localhost:5173"}
    assert "POST" in opt_res.headers.get("Access-Control-Allow-Methods", "")
    print(f"  [x] Preflight OPTIONS 200 OK with Access-Control-Allow-Origin: *")
    print(">>> TEST 7 PASSED: Native zero-dependency CORS operational.")

    # --------------------------------------------------------------------------
    # Post-Test Collection Preservation Verification
    # --------------------------------------------------------------------------
    print("\n--- POST-TEST VERIFICATION: ChromaDB Collection Preservation ---")
    final_ayush_count = chroma_client.get_collection("ip_sakti_ayush_v1").count()
    final_curcuma_count = chroma_client.get_collection("ip_sakti_curcuma_test_v1").count()
    print(f"  - ip_sakti_ayush_v1: Initial={initial_ayush_count}, Final={final_ayush_count}")
    print(f"  - ip_sakti_curcuma_test_v1: Initial={initial_curcuma_count}, Final={final_curcuma_count}")
    assert final_ayush_count == initial_ayush_count == 2150
    assert final_curcuma_count == initial_curcuma_count == 1297
    print(">>> POST-TEST VERIFICATION PASSED: Collections strictly preserved without mutation.")

    print("\n" + "=" * 80)
    print("ALL 7 API GATEWAY TEST SUITES COMPLETED WITH ZERO FAILURES!")
    print("=" * 80)


if __name__ == "__main__":
    run_gateway_tests()

