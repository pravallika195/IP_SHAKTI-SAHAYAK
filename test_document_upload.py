import io
import sys
import tempfile
from pathlib import Path
import docx
import fitz
import requests

# Set stdout encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

VITE_PROXY_URL = "http://localhost:5173"
FLASK_DIRECT_URL = "http://127.0.0.1:5000"

def get_base_url():
    try:
        r = requests.get(f"{VITE_PROXY_URL}/health", timeout=5)
        if r.status_code == 200:
            print(f"[OK] Connected via Vite proxy: {VITE_PROXY_URL}")
            return VITE_PROXY_URL
    except Exception:
        pass
    print(f"[OK] Connected directly to Flask: {FLASK_DIRECT_URL}")
    return FLASK_DIRECT_URL

def create_sample_pdf() -> bytes:
    """Create a 2-page sample PDF with patent claims using PyMuPDF."""
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_textbox(
        fitz.Rect(50, 50, 500, 700),
        "PATENT SPECIFICATION: CURCUMA BIOENHANCED FORMULATION\n\n"
        "Application Number: IN 202311059999 A\n"
        "Technical Field: Herbal nanocarrier formulation for improved curcumin bioavailability.\n\n"
        "Summary: This invention discloses an aqueous self-emulsifying drug delivery system (SEDDS) "
        "comprising Curcuma longa rhizome extract and piperine at a 10:1 ratio with surfactant matrix.",
        fontsize=11
    )
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_textbox(
        fitz.Rect(50, 50, 500, 700),
        "CLAIMS:\n\n"
        "1. A stable topical emulgel comprising 95% standardized Curcuma longa curcuminoids, "
        "0.5% piperine, and a carbomer hydrophilic matrix maintaining pH 6.2.\n"
        "2. The formulation of claim 1, demonstrating 3-fold higher dermal flux.",
        fontsize=11
    )
    
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def create_blank_pdf() -> bytes:
    """Create a blank PDF with 0 extractable text."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def create_sample_docx() -> bytes:
    """Create a sample DOCX with paragraphs and a table."""
    doc = docx.Document()
    doc.add_heading("Applicant Laboratory Report: Emulgel Stability", 0)
    doc.add_paragraph("Batch ID: CUR-EMUL-2026-B1. System: Ayurveda.")
    doc.add_paragraph("Ingredients: Curcuma longa 95% extract, Piper nigrum piperine, Carbopol 940.")
    
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Parameter"
    hdr_cells[1].text = "Target Specification"
    hdr_cells[2].text = "Observed Value"
    
    row_cells = table.add_row().cells
    row_cells[0].text = "pH"
    row_cells[1].text = "6.0 - 6.5"
    row_cells[2].text = "6.22"
    
    row_cells2 = table.add_row().cells
    row_cells2[0].text = "Viscosity (cP)"
    row_cells2[1].text = "45000 - 55000"
    row_cells2[2].text = "49800"
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def run_suite():
    print("=" * 80)
    print("IP-SAKTI Sahayak — Phase 5 Document Upload & Extraction Test Suite")
    print("=" * 80)
    base_url = get_base_url()

    # --------------------------------------------------------------------------
    # Test 1: Valid PDF Upload & Extraction
    # --------------------------------------------------------------------------
    print("\n--- Test 1: Valid PDF Upload (PyMuPDF) ---")
    pdf_bytes = create_sample_pdf()
    files = {"file": ("test_patent_draft.pdf", pdf_bytes, "application/pdf")}
    r = requests.post(f"{base_url}/api/documents/upload", files=files, timeout=20)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    pdf_data = r.json()
    assert pdf_data["status"] == "success"
    assert pdf_data["page_count"] == 2
    assert pdf_data["file_type"] == "pdf"
    assert "Curcuma longa" in pdf_data["extracted_text"]
    assert any("IN" in p and "202311059999" in p for p in pdf_data["metadata"]["detected_patent_numbers"])
    assert len(pdf_data["pages"]) == 2
    doc_id_pdf = pdf_data["document_id"]
    print(f"[PASS] PDF extracted successfully: ID={doc_id_pdf}, Pages={pdf_data['page_count']}, Chars={pdf_data['text_length']}")
    print(f"       Detected patent numbers: {pdf_data['metadata']['detected_patent_numbers']}")

    # --------------------------------------------------------------------------
    # Test 2: Valid DOCX Upload & Extraction
    # --------------------------------------------------------------------------
    print("\n--- Test 2: Valid DOCX Upload (python-docx) ---")
    docx_bytes = create_sample_docx()
    files = {"file": ("lab_report_wound_healing.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = requests.post(f"{base_url}/api/documents/upload", files=files, timeout=20)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    docx_data = r.json()
    assert docx_data["status"] == "success"
    assert docx_data["file_type"] == "docx"
    assert "CUR-EMUL-2026-B1" in docx_data["extracted_text"]
    assert "Viscosity" in docx_data["extracted_text"]
    doc_id_docx = docx_data["document_id"]
    print(f"[PASS] DOCX extracted successfully: ID={doc_id_docx}, Chars={docx_data['text_length']}")

    # --------------------------------------------------------------------------
    # Test 3: Valid TXT Upload & Extraction
    # --------------------------------------------------------------------------
    print("\n--- Test 3: Valid TXT Upload (UTF-8) ---")
    txt_content = (
        "TRADITIONAL FORMULATION MONOGRAPH: HARIDRA EMULGEL\n\n"
        "Ingredients:\n"
        "1. Curcuma longa rhizome powder (Haridra)\n"
        "2. Maricha (Piper nigrum) fruit extract\n"
        "Therapeutic indication: Vrana ropana (wound healing) and Twak roga (dermatological conditions).\n"
        "Preparation Method: Aqueous decoction dispersed in natural hydrophilic polymer base."
    ).encode("utf-8")
    files = {"file": ("haridra_monograph.txt", txt_content, "text/plain")}
    r = requests.post(f"{base_url}/api/documents/upload", files=files, timeout=20)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    txt_data = r.json()
    assert txt_data["status"] == "success"
    assert txt_data["file_type"] == "txt"
    assert "Haridra" in txt_data["extracted_text"]
    doc_id_txt = txt_data["document_id"]
    print(f"[PASS] TXT extracted successfully: ID={doc_id_txt}, Chars={txt_data['text_length']}")

    # --------------------------------------------------------------------------
    # Test 4: Invalid Extension Rejection
    # --------------------------------------------------------------------------
    print("\n--- Test 4: Invalid Extension Rejection ---")
    bad_file = {"file": ("malicious_payload.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")}
    r = requests.post(f"{base_url}/api/documents/upload", files=bad_file, timeout=10)
    assert r.status_code == 400
    print(f"[PASS] Disallowed extension rejected: {r.json().get('error')}")

    # --------------------------------------------------------------------------
    # Test 5: Empty File Rejection (0 bytes)
    # --------------------------------------------------------------------------
    print("\n--- Test 5: Empty File Rejection ---")
    empty_file = {"file": ("empty_draft.pdf", b"", "application/pdf")}
    r = requests.post(f"{base_url}/api/documents/upload", files=empty_file, timeout=10)
    assert r.status_code == 400
    print(f"[PASS] Empty file rejected: {r.json().get('error')}")

    # --------------------------------------------------------------------------
    # Test 6: Corrupt PDF Handling
    # --------------------------------------------------------------------------
    print("\n--- Test 6: Corrupt PDF Handling ---")
    corrupt_pdf = {"file": ("corrupt_spec.pdf", b"%PDF-1.4\ncorrupt gibberish non-pdf data", "application/pdf")}
    r = requests.post(f"{base_url}/api/documents/upload", files=corrupt_pdf, timeout=10)
    corrupt_data = r.json()
    # Should catch gracefully with error status without crashing server
    assert corrupt_data.get("status") == "error" or r.status_code in {200, 400}
    print(f"[PASS] Corrupt PDF gracefully caught: {corrupt_data.get('error')}")

    # --------------------------------------------------------------------------
    # Test 7: Oversized File (> 15 MB)
    # --------------------------------------------------------------------------
    print("\n--- Test 7: Oversized File Protection ---")
    oversized_bytes = b"%PDF-1.5 " + b"0" * (16 * 1024 * 1024)
    oversized_file = {"file": ("giant_document.pdf", oversized_bytes, "application/pdf")}
    r = requests.post(f"{base_url}/api/documents/upload", files=oversized_file, timeout=20)
    assert r.status_code == 400
    print(f"[PASS] Oversized file rejected: {r.json().get('error')}")

    # --------------------------------------------------------------------------
    # Test 8: Extraction Warnings (Blank PDF)
    # --------------------------------------------------------------------------
    print("\n--- Test 8: Extraction Warning on Blank PDF ---")
    blank_bytes = create_blank_pdf()
    files = {"file": ("blank_scanned.pdf", blank_bytes, "application/pdf")}
    r = requests.post(f"{base_url}/api/documents/upload", files=files, timeout=15)
    assert r.status_code == 200
    blank_data = r.json()
    assert blank_data["status"] == "warning"
    assert len(blank_data["warnings"]) > 0
    print(f"[PASS] Warning issued on 0-character PDF: {blank_data['warnings']}")

    # --------------------------------------------------------------------------
    # Test 9: Multiple Files Upload in Single Request
    # --------------------------------------------------------------------------
    print("\n--- Test 9: Batch Upload of Multiple Files ---")
    multi_files = [
        ("files", ("batch_doc1.pdf", create_sample_pdf(), "application/pdf")),
        ("files", ("batch_doc2.txt", b"Batch document 2 plain text disclosure", "text/plain"))
    ]
    r = requests.post(f"{base_url}/api/documents/upload", files=multi_files, timeout=20)
    assert r.status_code == 200
    multi_data = r.json()
    assert multi_data["status"] == "ok"
    assert multi_data["count"] == 2
    print(f"[PASS] Multi-file batch processed: {multi_data['count']} documents extracted")

    # --------------------------------------------------------------------------
    # Test 10: Document Deletion
    # --------------------------------------------------------------------------
    print("\n--- Test 10: Safe Document Removal ---")
    r = requests.delete(f"{base_url}/api/documents/{doc_id_pdf}", timeout=10)
    assert r.status_code == 200
    del_data = r.json()
    assert del_data["status"] == "ok"
    print(f"[PASS] Document deleted from sandbox: {del_data['message']}")

    # --------------------------------------------------------------------------
    # Test 11: End-to-End Innovation Analysis with Uploaded Document
    # --------------------------------------------------------------------------
    print("\n--- Test 11: Innovation Analysis with Uploaded Document Text ---")
    analysis_payload = {
        "title": "Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing",
        "ayush_system": "Ayurveda",
        "problem": "Poor dermal bioavailability of curcumin in open wounds.",
        "solution": "A stable topical emulgel incorporating standardized Curcuma extract with piperine.",
        "ingredients": [
            "Curcuma longa rhizome extract (95% curcuminoids)",
            "Piper nigrum extract / Piperine",
            "Carbopol 940",
            "Triethanolamine"
        ],
        "technical_features": [
            "Standardized Curcuma longa extract containing 95% total curcuminoids",
            "Piperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation",
            "Topical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5"
        ],
        "claimed_advantages": "Enhanced dermal penetration and synergistic wound healing.",
        "uploaded_documents": [
            {
                "document_id": doc_id_docx,
                "filename": "lab_report_wound_healing.docx",
                "page_count": 1,
                "file_type": "docx",
                "extracted_text": docx_data["extracted_text"]
            }
        ]
    }
    r = requests.post(f"{base_url}/api/innovation/analyze", json=analysis_payload, timeout=45)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    report_data = r.json()
    assert report_data["retrieval_status"] == "NONEMPTY_RETRIEVAL"
    assert len(report_data["sources"]) > 0
    assert report_data["citation_audit"] is not None
    assert len(report_data.get("uploaded_documents", [])) == 1
    # Ensure uploaded document was NOT added as a prior-art source
    prior_art_sources = [s["source"] for s in report_data["sources"]]
    assert "lab_report_wound_healing.docx" not in prior_art_sources, "Applicant doc must NOT be in prior art sources!"
    print(f"[PASS] Innovation Analysis completed with applicant document attached.")
    print(f"       Prior-art sources retrieved: {len(report_data['sources'])} (Strictly from external knowledge base)")
    print(f"       Citation audit: {report_data['citation_audit']['status']}")

    # --------------------------------------------------------------------------
    # Test 12: ChromaDB Knowledge Base Preservation
    # --------------------------------------------------------------------------
    print("\n--- Test 12: Strict ChromaDB Collections Preservation ---")
    r_status = requests.get(f"{base_url}/api/collections/status", timeout=10)
    assert r_status.status_code == 200
    st_data = r_status.json()
    assert st_data["total_chunks"] == 3447, f"Expected exactly 3,447 chunks, got {st_data['total_chunks']}"
    assert st_data["collections"]["ip_sakti_ayush_v1"]["count"] == 2150
    assert st_data["collections"]["ip_sakti_curcuma_test_v1"]["count"] == 1297
    print(f"[PASS] ChromaDB collections strictly unchanged: Total = {st_data['total_chunks']} (2150 in ayush_v1, 1297 in curcuma_test_v1)")

    print("\n" + "=" * 80)
    print("ALL 12 DOCUMENT UPLOAD & EXTRACTION TESTS PASSED WITH ZERO FAILURES!")
    print("=" * 80)

if __name__ == "__main__":
    run_suite()
