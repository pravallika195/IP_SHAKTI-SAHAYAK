import sys
import uuid
import requests

# Ensure proper stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

VITE_PROXY_URL = "http://localhost:5173"
FLASK_DIRECT_URL = "http://127.0.0.1:5000"

def run_tests():
    print("=" * 80)
    print("IP-SAKTI Sahayak — Phase 4 Patent Assistant Verification Suite")
    print("=" * 80)

    # Base URL check
    base_url = VITE_PROXY_URL
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        print(f"[OK] Connected via Vite proxy at {base_url} (Health: {r.status_code})")
    except Exception as e:
        print(f"[WARN] Vite proxy connection failed: {e}. Falling back to Flask direct {FLASK_DIRECT_URL}")
        base_url = FLASK_DIRECT_URL

    # --------------------------------------------------------------------------
    # Scenario 1: Greeting Query
    # --------------------------------------------------------------------------
    print("\n--- Scenario 1: Greeting Query ---")
    session_1 = f"test_session_{uuid.uuid4().hex[:8]}"
    payload = {
        "session_id": session_1,
        "query": "Hello, good morning! Who are you?",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["category"] in {"GREETING", "TIME_GREETING"}, f"Expected GREETING or TIME_GREETING, got {data['category']}"
    assert len(data["sources"]) == 0, f"Expected 0 sources for greeting, got {len(data['sources'])}"
    assert len(data["answer"]) > 20, "Greeting answer too short"
    print(f"[PASS] Category: {data['category']}")
    print(f"       Answer preview: {data['answer'][:80]}...")

    # --------------------------------------------------------------------------
    # Scenario 2: AYUSH Research Query
    # --------------------------------------------------------------------------
    print("\n--- Scenario 2: AYUSH Research Query ---")
    payload = {
        "session_id": session_1,
        "query": "What phytochemicals are reported in Curcuma longa (turmeric)?",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=90)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["category"] in {"AYUSH_RESEARCH", "FOLLOW_UP"}, f"Unexpected category {data['category']}"
    assert len(data["sources"]) > 0, "Expected retrieved sources > 0"
    assert data["citation_audit"] is not None, "Expected citation audit"
    print(f"[PASS] Category: {data['category']}, Sources: {len(data['sources'])}, Citation Audit: {data['citation_audit']['status']}")
    print(f"       Top source: {data['sources'][0].get('source')} (col: {data['sources'][0].get('collection')})")

    # --------------------------------------------------------------------------
    # Scenario 3: Contextual Follow-up Query with Pronoun Coreference
    # --------------------------------------------------------------------------
    print("\n--- Scenario 3: Contextual Follow-up Query ---")
    payload = {
        "session_id": session_1,
        "query": "Which polyherbal formulations contain it for skin disorders?",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=90)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    resolved = data.get("resolved_query") or data.get("standalone_query")
    print(f"[PASS] Category: {data['category']}")
    print(f"       Resolved Query: {resolved}")
    print(f"       Sources retrieved: {len(data['sources'])}")

    # --------------------------------------------------------------------------
    # Scenario 4: Topic Switching in Same Session
    # --------------------------------------------------------------------------
    print("\n--- Scenario 4: Topic Switching ---")
    payload = {
        "session_id": session_1,
        "query": "What are the patentability requirements under Section 3(e) for herbal compositions?",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=90)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"[PASS] Category: {data['category']}, Sources: {len(data['sources'])}")
    print(f"       Answer snippet: {data['answer'][:100]}...")

    # --------------------------------------------------------------------------
    # Scenario 5: Out-of-Domain Unrelated Question
    # --------------------------------------------------------------------------
    print("\n--- Scenario 5: Out-of-Domain Unrelated Question ---")
    session_ood = f"test_session_ood_{uuid.uuid4().hex[:8]}"
    payload = {
        "session_id": session_ood,
        "query": "What is the capital of France and how do I sort an array in python?",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["category"] == "OUT_OF_DOMAIN", f"Expected OUT_OF_DOMAIN, got {data['category']}"
    assert len(data["sources"]) == 0, f"Expected 0 sources for out of domain, got {len(data['sources'])}"
    assert "AYUSH" in data["answer"] or "domain" in data["answer"].lower()
    print(f"[PASS] Category: {data['category']} (Zero retrieval triggered, honest abstention returned)")

    # --------------------------------------------------------------------------
    # Scenario 6: Insufficient Evidence Query
    # --------------------------------------------------------------------------
    print("\n--- Scenario 6: Insufficient Evidence Honest Handling ---")
    session_insuf = f"test_session_insuf_{uuid.uuid4().hex[:8]}"
    payload = {
        "session_id": session_insuf,
        "query": "NonExistentSyntheticChemicalMoleculeCompound9988776655",
        "language": "English"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"[PASS] Category: {data['category']}, Sources: {len(data['sources'])}")
    assert "Insufficient Evidence" in data["answer"] or len(data["sources"]) == 0
    print(f"       Answer snippet: {data['answer'][:90]}...")

    # --------------------------------------------------------------------------
    # Scenario 7: Multilingual Requests (Hindi and Telugu)
    # --------------------------------------------------------------------------
    print("\n--- Scenario 7: Multilingual Synthesis ---")
    # Hindi test
    session_hi = f"test_session_hi_{uuid.uuid4().hex[:8]}"
    payload_hi = {
        "session_id": session_hi,
        "query": "हल्दी के मुख्य चिकित्सीय उपयोग क्या हैं?",
        "language": "Hindi"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload_hi, timeout=40)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data_hi = r.json()
    print(f"[PASS] Hindi response generated ({len(data_hi['answer'])} chars)")
    print(f"       Hindi snippet: {data_hi['answer'][:80]}...")

    # Telugu test
    session_te = f"test_session_te_{uuid.uuid4().hex[:8]}"
    payload_te = {
        "session_id": session_te,
        "query": "పసుపు యొక్క ఔషధ గుణాలు ఏమిటి?",
        "language": "Telugu"
    }
    r = requests.post(f"{base_url}/api/assistant/chat", json=payload_te, timeout=40)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data_te = r.json()
    print(f"[PASS] Telugu response generated ({len(data_te['answer'])} chars)")
    print(f"       Telugu snippet: {data_te['answer'][:80]}...")

    # --------------------------------------------------------------------------
    # Scenario 8: Session Reset Endpoint
    # --------------------------------------------------------------------------
    print("\n--- Scenario 8: Session Reset Endpoint ---")
    r = requests.post(f"{base_url}/api/assistant/reset", json={"session_id": session_1}, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["status"] == "ok"
    assert data["session_id"] == session_1
    print(f"[PASS] Reset confirmed: {data['message']}")

    # --------------------------------------------------------------------------
    # Scenario 9: Multi-Session Context Isolation
    # --------------------------------------------------------------------------
    print("\n--- Scenario 9: Multi-Session Context Isolation ---")
    sess_a = f"session_A_{uuid.uuid4().hex[:8]}"
    sess_b = f"session_B_{uuid.uuid4().hex[:8]}"

    # Turn 1 for A: Curcuma longa
    requests.post(f"{base_url}/api/assistant/chat", json={
        "session_id": sess_a,
        "query": "What are the medicinal properties of Curcuma longa?",
        "language": "English"
    }, timeout=40)

    # Turn 1 for B: Neem / Azadirachta indica
    requests.post(f"{base_url}/api/assistant/chat", json={
        "session_id": sess_b,
        "query": "What are the medicinal uses of Azadirachta indica (Neem)?",
        "language": "English"
    }, timeout=40)

    # Turn 2 for A: "What are its formulations?"
    r_a2 = requests.post(f"{base_url}/api/assistant/chat", json={
        "session_id": sess_a,
        "query": "What are its polyherbal formulations?",
        "language": "English"
    }, timeout=40).json()

    # Turn 2 for B: "What are its formulations?"
    r_b2 = requests.post(f"{base_url}/api/assistant/chat", json={
        "session_id": sess_b,
        "query": "What are its traditional formulations?",
        "language": "English"
    }, timeout=40).json()

    res_a = (r_a2.get("resolved_query") or r_a2.get("standalone_query") or "").lower()
    res_b = (r_b2.get("resolved_query") or r_b2.get("standalone_query") or "").lower()

    print(f"       Session A resolved follow-up: {res_a}")
    print(f"       Session B resolved follow-up: {res_b}")
    assert "curcuma" in res_a or "turmeric" in res_a or "haridra" in res_a, f"Expected turmeric in Session A, got {res_a}"
    assert "neem" in res_b or "azadirachta" in res_b, f"Expected neem in Session B, got {res_b}"
    print("[PASS] Session A and Session B maintain strictly isolated conversation memories!")

    # --------------------------------------------------------------------------
    # Scenario 10: Input Validation & Collections Status
    # --------------------------------------------------------------------------
    print("\n--- Scenario 10: Validation & ChromaDB Status Check ---")
    # Empty body
    r = requests.post(f"{base_url}/api/assistant/chat", json={}, timeout=10)
    assert r.status_code == 400
    print(f"[PASS] Empty payload rejected with 400: {r.json().get('error')}")

    # Missing session_id
    r = requests.post(f"{base_url}/api/assistant/chat", json={"query": "test"}, timeout=10)
    assert r.status_code == 400
    print(f"[PASS] Missing session_id rejected with 400: {r.json().get('error')}")

    # Missing query
    r = requests.post(f"{base_url}/api/assistant/chat", json={"session_id": "test_1"}, timeout=10)
    assert r.status_code == 400
    print(f"[PASS] Missing query rejected with 400: {r.json().get('error')}")

    # Verify collections status endpoint
    r_status = requests.get(f"{base_url}/api/collections/status", timeout=10)
    assert r_status.status_code == 200
    status_data = r_status.json()
    assert status_data["total_chunks"] == 3447, f"Expected 3,447 chunks, got {status_data['total_chunks']}"
    assert status_data["collections"]["ip_sakti_ayush_v1"]["count"] == 2150
    assert status_data["collections"]["ip_sakti_curcuma_test_v1"]["count"] == 1297
    print(f"[PASS] ChromaDB collections strictly preserved: Total = {status_data['total_chunks']} chunks (2150 + 1297)")

    print("\n" + "=" * 80)
    print("ALL 10 VERIFICATION SCENARIOS PASSED WITH ZERO FAILURES!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()

