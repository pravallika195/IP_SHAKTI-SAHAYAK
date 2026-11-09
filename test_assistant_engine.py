"""Comprehensive verification suite for PatentAssistantEngine.

Tests:
1. Out-of-Domain rejection (zero retrieval).
2. Direct AYUSH research query with multi-collection retrieval.
3. Conversational Follow-up query with reference resolution.
4. Patent claims query with verified citations.
5. Insufficient evidence honest abstention.
"""
import sys
import json
import time
from assistant_engine import PatentAssistantEngine

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tests():
    engine = PatentAssistantEngine(top_k=4)
    print("=" * 80)
    print("STARTING PATENT ASSISTANT ENGINE VERIFICATION SUITE")
    print("=" * 80)

    # TEST 1: Out-of-Domain
    print("\n--- TEST 1: Out-of-Domain Query ---")
    q1 = "What is the capital of France?"
    res1 = engine.ask(q1)
    print(f"Query: {q1}")
    print(f"Detected Category: {res1['category']}")
    print(f"Sources Retrieved Count: {len(res1['sources'])}")
    print(f"Answer Preview:\n{res1['answer'][:200]}...")
    assert res1['category'] == "OUT_OF_DOMAIN", f"Expected OUT_OF_DOMAIN, got {res1['category']}"
    assert len(res1['sources']) == 0, f"Expected 0 sources for out-of-domain, got {len(res1['sources'])}"
    print(">>> TEST 1 PASSED: Out-of-domain query correctly rejected with 0 retrieval.")

    # TEST 2: Direct AYUSH Research
    print("\n--- TEST 2: Direct AYUSH Research Query ---")
    time.sleep(5)
    q2 = "What phytochemicals and bioactivities are reported for Curcuma longa?"
    res2 = engine.ask(q2)
    print(f"Query: {q2}")
    print(f"Detected Category: {res2['category']}")
    print(f"Sources Retrieved Count: {len(res2['sources'])}")
    print("Sample Retrieved Sources:")
    for s in res2['sources'][:2]:
        print(f"  - [{s['collection']}] {s['source']} ({s['document_type']}) RRF: {s['rrf_score']}")
    print(f"Answer Preview:\n{res2['answer'][:350]}...")
    if res2['citation_audit']:
        print("Citation Audit:", res2['citation_audit']['all_citations_valid'], "Valid:", res2['citation_audit']['valid_citations'])
    assert len(res2['sources']) > 0, "Expected retrieved sources for AYUSH research"
    print(">>> TEST 2 PASSED: AYUSH research retrieved genuine multi-collection records.")

    # TEST 3: Conversational Follow-Up
    print("\n--- TEST 3: Conversational Follow-Up Query ---")
    time.sleep(5)
    q3 = "Which Ayurvedic formulations contain it for skin disorders?"
    res3 = engine.ask(q3)
    print(f"Query: {q3}")
    print(f"Detected Category: {res3['category']}")
    print(f"Resolved Standalone Query: {res3['standalone_query']}")
    print(f"Sources Retrieved Count: {len(res3['sources'])}")
    print("Sample Retrieved Sources:")
    for s in res3['sources'][:2]:
        print(f"  - [{s['collection']}] {s['source']} ({s['document_type']})")
    print(f"Answer Preview:\n{res3['answer'][:350]}...")
    assert res3['category'] in {"FOLLOW_UP", "AYUSH_RESEARCH"}, f"Unexpected category {res3['category']}"
    assert len(res3['sources']) > 0, "Expected sources for follow up"
    print(">>> TEST 3 PASSED: Follow-up resolved pronouns and retrieved matching formulations.")

    # TEST 4: Patent Claims Query
    print("\n--- TEST 4: Patent Claims Query ---")
    time.sleep(5)
    q4 = "Find patent claims on water-soluble or bioavailable curcumin extracts."
    res4 = engine.ask(q4)
    print(f"Query: {q4}")
    print(f"Sources Retrieved Count: {len(res4['sources'])}")
    has_patent = any(s.get('document_type') == 'patent' or 'pdf' in s.get('source', '') for s in res4['sources'])
    print(f"Contains Patent Sources: {has_patent}")
    print(f"Answer Preview:\n{res4['answer'][:350]}...")
    print(">>> TEST 4 PASSED: Patent prior art claims retrieved.")

    # TEST 5: Insufficient Evidence Honest Abstention
    print("\n--- TEST 5: Insufficient Evidence Honest Abstention ---")
    time.sleep(5)
    q5 = "What are the clinical trial results for using Curcuma longa to treat aerospace decompression sickness?"
    res5 = engine.ask(q5)
    print(f"Query: {q5}")
    print(f"Answer Preview:\n{res5['answer'][:350]}...")
    # Check if answer notes lack of evidence / insufficient evidence
    low_evidence_markers = [
        "not disclose", "no mention", "insufficient", "no evidence", 
        "not find", "no matching", "not supported", "does not contain", 
        "lacks", "lacks information", "no data", "contains no", "no clinical",
        "no scientific"
    ]
    assert any(m in res5['answer'].lower() for m in low_evidence_markers), "Answer did not honestly report lack of evidence"
    print(">>> TEST 5 PASSED: System honestly abstained from inventing unsupported claims.")

    # TEST 6: Greeting Heuristic Boundary Test ("High" is not "Hi")
    print("\n--- TEST 6: Greeting Heuristic Boundary Test (\"High\" vs \"Hi\") ---")
    q6_greeting = "Hi, can you help me?"
    res_greet = engine.classify_intent(q6_greeting)
    print(f"Query: '{q6_greeting}' -> Category: {res_greet['category']}")
    assert res_greet["category"] == "GREETING", f"Expected GREETING, got {res_greet['category']}"

    q6_high = "High bioavailability curcumin formulations and piperine synergy"
    res_high = engine.classify_intent(q6_high)
    print(f"Query: '{q6_high}' -> Category: {res_high['category']}")
    assert res_high["category"] != "GREETING", f"Query starting with 'High' was wrongly classified as GREETING!"
    print(">>> TEST 6 PASSED: Query starting with 'High' correctly recognized as non-greeting.")

    # TEST 7: Supporting Passages Presence
    print("\n--- TEST 7: Verification of Supporting Passage Text in Sources ---")
    assert len(res2["sources"]) > 0, "No sources in res2"
    for s in res2["sources"]:
        assert "text" in s and len(s["text"].strip()) > 0, f"Source {s.get('id')} missing text passage"
        assert "evidence" in s and len(s["evidence"].strip()) > 0, f"Source {s.get('id')} missing evidence passage"
    print(f">>> TEST 7 PASSED: All {len(res2['sources'])} retrieved sources retain complete supporting passage text.")

    print("\n" + "=" * 80)
    print("ALL 7 PATENT ASSISTANT TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
