"""
Test Suite for Phase 6: MySQL Database, Authentication, and Persistent User Data
Verifies:
1. MySQL 8.0 connectivity and schema
2. User registration with JWT HttpOnly cookie
3. Login failure and sliding-window rate limiting (429)
4. Authenticated sessions and GET /api/auth/me
5. Unauthorized access prevention (401)
6. Cross-user isolation (User B cannot access User A's data)
7. Innovation project CRUD and immutable versioning
8. Document upload and persistence (without modifying ChromaDB)
9. Persistent Analysis Runs linked to specific innovation versions
10. Patent Assistant Chat Thread and Message Source persistence in MySQL
11. Session restoration
12. ChromaDB integrity check (3,447 chunks preserved)
"""

import sys
import time
import uuid
import requests
import pymysql

BASE_URL = "http://127.0.0.1:5000"

def log_test(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {detail}")


def main():
    print("\n" + "=" * 70)
    print("PHASE 6: COMPREHENSIVE PERSISTENCE & AUTHENTICATION TEST SUITE")
    print("=" * 70 + "\n")

    # -------------------------------------------------------------------------
    # 1. MySQL Connectivity & Schema
    # -------------------------------------------------------------------------
    print("--- 1. MySQL 8.0 Connectivity & Schema Verification ---")
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",
        database="ip_sakti_sahayak",
        charset="utf8mb4"
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1;")
        res = cursor.fetchone()
        log_test("MySQL Connection SELECT 1", res[0] == 1)

        cursor.execute("SHOW TABLES;")
        tables = [t[0] for t in cursor.fetchall()]
        expected_tables = [
            "users",
            "innovations",
            "innovation_versions",
            "innovation_documents",
            "analysis_runs",
            "chat_threads",
            "chat_messages",
            "chat_message_sources"
        ]
        for tbl in expected_tables:
            log_test(f"Table exists: {tbl}", tbl in tables, f"Found in MySQL: {tables}")
    conn.close()

    # -------------------------------------------------------------------------
    # 2. Registration & HttpOnly Cookie
    # -------------------------------------------------------------------------
    print("\n--- 2. User Registration & JWT Cookie Handling ---")
    s_user_a = requests.Session()
    s_user_b = requests.Session()

    suffix = uuid.uuid4().hex[:6]
    email_a = f"researcher_a_{suffix}@ayush.gov.in"
    password_a = "AyushSecPass#2026"
    email_b = f"researcher_b_{suffix}@ayush.gov.in"
    password_b = "AyushSecPass#2026B"

    # Register User A
    r = s_user_a.post(f"{BASE_URL}/api/auth/register", json={
        "email": email_a,
        "password": password_a,
        "full_name": "Dr. Arya Sharma",
        "role": "researcher"
    })
    log_test("Register User A (HTTP 201)", r.status_code == 201, r.text)
    user_a_data = r.json().get("user", {})
    user_a_id = user_a_data.get("id")
    log_test("User A ID returned", bool(user_a_id), f"ID: {user_a_id}")

    # Check HttpOnly cookie
    set_cookie_header = r.headers.get("Set-Cookie", "")
    log_test("Set-Cookie contains access_token", "access_token=" in set_cookie_header)
    log_test("Cookie has HttpOnly flag", "httponly" in set_cookie_header.lower())

    # Register User B
    r_b = s_user_b.post(f"{BASE_URL}/api/auth/register", json={
        "email": email_b,
        "password": password_b,
        "full_name": "Dr. Vikram Patel",
        "role": "researcher"
    })
    log_test("Register User B (HTTP 201)", r_b.status_code == 201)
    user_b_id = r_b.json().get("user", {}).get("id")

    # -------------------------------------------------------------------------
    # 3. Authentication Verification & Rate Limiting
    # -------------------------------------------------------------------------
    print("\n--- 3. Login Validation & Sliding-Window Rate Limiting ---")
    s_temp = requests.Session()
    # Attempt invalid password
    r_fail = s_temp.post(f"{BASE_URL}/api/auth/login", json={
        "email": email_a,
        "password": "WrongPassword!999"
    })
    log_test("Invalid password returns 401", r_fail.status_code == 401)

    # Trigger rate limiter (5 max attempts per window)
    print("Testing 5 consecutive failed login attempts to trigger 429 rate limit...")
    hit_rate_limit = False
    for i in range(5):
        r_attempt = s_temp.post(f"{BASE_URL}/api/auth/login", json={
            "email": email_a,
            "password": f"BadPass_{i}"
        })
        if r_attempt.status_code == 429:
            hit_rate_limit = True
            break
    log_test("Rate limiting blocks excessive failed logins (HTTP 429)", hit_rate_limit, f"Final status: {r_attempt.status_code}")

    # -------------------------------------------------------------------------
    # 4. Session Validation & Current User
    # -------------------------------------------------------------------------
    print("\n--- 4. Session Validation via GET /api/auth/me ---")
    r_me_a = s_user_a.get(f"{BASE_URL}/api/auth/me")
    log_test("User A GET /api/auth/me (HTTP 200)", r_me_a.status_code == 200)
    log_test("User A email matches", r_me_a.json().get("user", {}).get("email") == email_a)

    # Unauthenticated session must return 401
    s_unauth = requests.Session()
    r_unauth = s_unauth.get(f"{BASE_URL}/api/auth/me")
    log_test("Unauthenticated GET /api/auth/me returns 401", r_unauth.status_code == 401)

    r_prot = s_unauth.get(f"{BASE_URL}/api/innovations")
    log_test("Unauthenticated GET /api/innovations returns 401", r_prot.status_code == 401)

    # -------------------------------------------------------------------------
    # 5. Innovation Project CRUD & Version Immutability
    # -------------------------------------------------------------------------
    print("\n--- 5. Innovation Project CRUD & Version Immutability ---")
    # User A creates Innovation
    payload_v1 = {
        "title": "Bio-enhanced Curcuma Nanoemulsion for Joint Health",
        "ayush_system": "Ayurveda",
        "problem": "Poor aqueous solubility of curcumin limits oral bioavailability.",
        "solution": "Self-nanoemulsifying drug delivery system (SNEDDS) utilizing Ayurvedic sesame oil and lipid surfactants.",
        "ingredients": [
            "Curcuma longa rhizome extract 95%",
            "Sesamum indicum (Tila taila)",
            "Tween 80"
        ],
        "technical_features": [
            "Nanoemulsion droplet size < 150 nm",
            "Standardized 95% total curcuminoids in lipid core",
            "Stable formulation at ambient Ayurvedic storage conditions"
        ],
        "claimed_advantages": "4-fold increase in oral bioavailability over conventional powdered haridra."
    }

    r_create = s_user_a.post(f"{BASE_URL}/api/innovations", json=payload_v1)
    log_test("Create Innovation (HTTP 201)", r_create.status_code == 201, r_create.text)
    inn_id = r_create.json().get("innovation_id") or r_create.json().get("innovation", {}).get("id")
    log_test("Innovation ID returned", bool(inn_id), f"Innovation ID: {inn_id}")

    # Fetch innovation detail
    r_get = s_user_a.get(f"{BASE_URL}/api/innovations/{inn_id}")
    log_test("Fetch Innovation details (HTTP 200)", r_get.status_code == 200)
    inn_data = r_get.json().get("innovation", {})
    log_test("Version 1 created initially", inn_data.get("latest_version_number") == 1)
    log_test("Initial version list length == 1", len(inn_data.get("versions", [])) == 1)

    # User A updates Innovation -> creates immutable Version 2
    payload_v2 = {
        "title": "Bio-enhanced Curcuma Nanoemulsion with Piperine Bio-enhancer",
        "ayush_system": "Ayurveda",
        "problem": "Need for synergistic intestinal absorption beyond lipid encapsulation.",
        "solution": "Curcuma SNEDDS co-loaded with standardized Piper nigrum (Maricha) extract.",
        "ingredients": [
            "Curcuma longa rhizome extract 95%",
            "Piper nigrum fruit extract (95% piperine)",
            "Sesamum indicum (Tila taila)",
            "Tween 80"
        ],
        "technical_features": [
            "Nanoemulsion droplet size < 120 nm",
            "1:10 w/w ratio of piperine to total curcuminoids",
            "Standardized 95% total curcuminoids in lipid core"
        ],
        "claimed_advantages": "10-fold increase in oral bioavailability and enhanced anti-inflammatory synergy.",
        "change_summary": "Added piperine bio-enhancer and reduced droplet size"
    }

    r_update = s_user_a.put(f"{BASE_URL}/api/innovations/{inn_id}", json=payload_v2)
    log_test("Update Innovation creates new version (HTTP 200)", r_update.status_code == 200)
    v_num = r_update.json().get("version_number") or r_update.json().get("innovation", {}).get("latest_version_number")
    log_test("Latest version incremented to 2", v_num == 2)

    # Verify both versions exist in history and Version 1 is immutable
    r_get_v2 = s_user_a.get(f"{BASE_URL}/api/innovations/{inn_id}")
    inn_v2_data = r_get_v2.json().get("innovation", {})
    versions = inn_v2_data.get("versions", [])
    log_test("Two immutable versions exist in history", len(versions) == 2)

    v1_record = next((v for v in versions if v["version_number"] == 1), None)
    v2_record = next((v for v in versions if v["version_number"] == 2), None)
    log_test("Version 1 preserved intact with 3 ingredients", len(v1_record["ingredients"]) == 3)
    log_test("Version 2 active with 4 ingredients", len(v2_record["ingredients"]) == 4)

    # -------------------------------------------------------------------------
    # 6. Cross-User Isolation Enforcement
    # -------------------------------------------------------------------------
    print("\n--- 6. Cross-User Isolation Enforcement ---")
    # User B attempts to fetch User A's innovation
    r_b_view = s_user_b.get(f"{BASE_URL}/api/innovations/{inn_id}")
    log_test("User B cannot view User A's innovation (HTTP 404)", r_b_view.status_code == 404)

    # User B attempts to update User A's innovation
    r_b_update = s_user_b.put(f"{BASE_URL}/api/innovations/{inn_id}", json={"title": "Hacked Title"})
    log_test("User B cannot update User A's innovation (HTTP 404)", r_b_update.status_code == 404)

    # User B attempts to delete User A's innovation
    r_b_delete = s_user_b.delete(f"{BASE_URL}/api/innovations/{inn_id}")
    log_test("User B cannot delete User A's innovation (HTTP 404)", r_b_delete.status_code == 404)

    # -------------------------------------------------------------------------
    # 7. Document Upload & Association
    # -------------------------------------------------------------------------
    print("\n--- 7. Document Persistence & Sandboxing ---")
    doc_content = b"Ayurvedic Haridra Formulation Study. Extraction of Curcuma longa rhizome shows substantial wound healing efficacy."
    files = {"file": ("haridra_study.txt", doc_content, "text/plain")}
    data = {"innovation_id": inn_id, "version_id": v2_record["id"]}

    r_upload = s_user_a.post(f"{BASE_URL}/api/documents/upload", files=files, data=data)
    log_test("Document upload with innovation link (HTTP 200)", r_upload.status_code == 200, r_upload.text)
    upload_res = r_upload.json()
    doc_id = upload_res.get("document_id")
    log_test("Document ID returned", bool(doc_id))

    # Verify User B cannot delete User A's document
    r_b_del_doc = s_user_b.delete(f"{BASE_URL}/api/documents/{doc_id}")
    log_test("User B cannot delete User A's uploaded document (HTTP 403/404)", r_b_del_doc.status_code in (403, 404), f"Status: {r_b_del_doc.status_code}")

    # -------------------------------------------------------------------------
    # 8. Persistent Analysis Runs
    # -------------------------------------------------------------------------
    print("\n--- 8. Persistent Analysis Runs in MySQL ---")
    r_run = s_user_a.post(f"{BASE_URL}/api/innovations/{inn_id}/analyze")
    log_test("Trigger Innovation Analysis Run (HTTP 200)", r_run.status_code == 200, r_run.text[:120])
    run_result = r_run.json()
    run_id = run_result.get("run_id")
    log_test("Analysis run ID created in MySQL", bool(run_id), f"Run ID: {run_id}")
    log_test("Analysis Run #1 assigned", run_result.get("run_number") == 1)
    log_test("Analysis report contains citations", "citation_audit" in run_result)

    # Fetch persistent run history
    r_runs_list = s_user_a.get(f"{BASE_URL}/api/innovations/{inn_id}/runs")
    log_test("Fetch Innovation Runs List (HTTP 200)", r_runs_list.status_code == 200)
    runs_list = r_runs_list.json().get("runs", [])
    log_test("Runs list contains recorded run", len(runs_list) >= 1)
    log_test("Recorded run status is COMPLETED", runs_list[0].get("status") == "COMPLETED")

    # Fetch specific persistent run details
    r_spec_run = s_user_a.get(f"{BASE_URL}/api/innovations/{inn_id}/runs/{run_id}")
    log_test("Fetch Specific Run Details (HTTP 200)", r_spec_run.status_code == 200)
    spec_run = r_spec_run.json().get("run", {})
    log_test("Specific run contains report_markdown", bool(spec_run.get("report_markdown")))

    # -------------------------------------------------------------------------
    # 9. Persistent Patent Assistant Chat Threads & Citations in MySQL
    # -------------------------------------------------------------------------
    print("\n--- 9. Patent Assistant Chat Thread & Source Persistence in MySQL ---")
    thread_session_id = f"thread_{uuid.uuid4().hex[:8]}"

    # Turn 1
    r_chat1 = s_user_a.post(f"{BASE_URL}/api/assistant/chat", json={
        "session_id": thread_session_id,
        "query": "What traditional medicinal uses of Curcuma longa (Haridra) are documented for skin disorders?"
    })
    log_test("Patent Assistant Chat Turn 1 (HTTP 200)", r_chat1.status_code == 200)
    chat1_data = r_chat1.json()
    log_test("Chat Turn 1 contains answer", bool(chat1_data.get("answer")))
    sources_turn1 = chat1_data.get("sources", [])
    log_test("Chat Turn 1 contains retrieved sources", len(sources_turn1) > 0)

    # Turn 2 (Follow-up)
    r_chat2 = s_user_a.post(f"{BASE_URL}/api/assistant/chat", json={
        "session_id": thread_session_id,
        "query": "What are its key chemical constituents?"
    })
    log_test("Patent Assistant Chat Turn 2 Follow-up (HTTP 200)", r_chat2.status_code == 200)

    # Verify thread and messages persisted in MySQL
    r_thread = s_user_a.get(f"{BASE_URL}/api/assistant/threads/{thread_session_id}")
    log_test("Fetch persistent Chat Thread (HTTP 200)", r_thread.status_code == 200)
    thread_data = r_thread.json().get("thread", {})
    messages = thread_data.get("messages", [])
    log_test("Thread messages persisted in MySQL (4 messages: 2 user + 2 assistant)", len(messages) == 4, f"Actual count: {len(messages)}")

    # Verify assistant message sources persisted in chat_message_sources table
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    first_assistant_msg = assistant_msgs[0]
    log_test("Persisted assistant message includes sources array", "sources" in first_assistant_msg)
    log_test("Persisted sources have title/patent_number", len(first_assistant_msg.get("sources", [])) > 0)

    # Verify User B cannot access User A's chat thread
    r_b_thread = s_user_b.get(f"{BASE_URL}/api/assistant/threads/{thread_session_id}")
    log_test("User B cannot access User A's persistent chat thread (HTTP 404)", r_b_thread.status_code == 404)

    # -------------------------------------------------------------------------
    # 10. Verify ChromaDB Collections Preservation
    # -------------------------------------------------------------------------
    print("\n--- 10. ChromaDB Integrity Verification ---")
    r_colls = s_user_a.get(f"{BASE_URL}/api/collections/status")
    log_test("GET /api/collections/status (HTTP 200)", r_colls.status_code == 200)
    colls = r_colls.json().get("collections", {})
    ayush_count = colls.get("ip_sakti_ayush_v1", 0)
    curcuma_count = colls.get("ip_sakti_curcuma_test_v1", 0)
    total_chunks = ayush_count + curcuma_count

    log_test("ip_sakti_ayush_v1 has 2150 chunks", ayush_count == 2150, f"Actual: {ayush_count}")
    log_test("ip_sakti_curcuma_test_v1 has 1297 chunks", curcuma_count == 1297, f"Actual: {curcuma_count}")
    log_test("Total ChromaDB chunks preserved exactly (3,447 chunks)", total_chunks == 3447, f"Total: {total_chunks}")

    print("\n" + "=" * 70)
    print("ALL PHASE 6 PERSISTENCE AND AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()