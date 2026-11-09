"""Flask REST API Gateway for IP-SAKTI Sahayak.

Phase 6 Architecture:
1. MySQL 8 Database Integration with SQLAlchemy and Flask-Migrate.
2. User Authentication (JWT via HttpOnly cookies, bcrypt hashing, rate limiting).
3. Innovation Persistence with Immutable Versioning.
4. Analysis Run Persistence and Audit History.
5. Sandboxed Document Upload with Ownership Verification.
6. Persistent Patent Assistant Research Threads and Grounded Citation Sources.
7. Diagnostics & Health (GET /health, GET /api/collections/status).
"""
from __future__ import annotations
import logging
import re
import threading
from datetime import datetime
from typing import Any

from flask import Flask, g, jsonify, request
from flask_migrate import Migrate

from assistant_engine import PatentAssistantEngine
from auth import (
    clear_auth_cookie,
    clear_failed_attempts,
    create_access_token,
    decode_access_token,
    get_token_from_request,
    is_rate_limited,
    login_required,
    record_failed_attempt,
    set_auth_cookie
)
from config import COLLECTION_NAME, TOP_K
from database import db, ensure_database_exists, init_db
from document_extractor import get_document_extractor
from innovation_engine import InnovationAnalysisEngine
from models import (
    AnalysisRun,
    ChatMessage,
    ChatMessageSource,
    ChatThread,
    Innovation,
    InnovationDocument,
    InnovationVersion,
    User
)
from rag_pipeline import RAGPipeline
from vector_store import get_client, get_or_create_collection

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize MySQL Database and Migrations
init_db(app)
migrate = Migrate(app, db)

# Thread-safe session storage for active Assistant engine instances
_sessions_lock = threading.Lock()
_assistant_sessions: dict[str, PatentAssistantEngine] = {}

# Engine singletons for stateless operations
_pipeline = None
_innovation_engine = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline(top_k=TOP_K)
    return _pipeline


def get_innovation_engine() -> InnovationAnalysisEngine:
    global _innovation_engine
    if _innovation_engine is None:
        _innovation_engine = InnovationAnalysisEngine(top_k=3)
    return _innovation_engine


def get_authenticated_user_from_request() -> User | None:
    """Optional auth helper that retrieves user if valid token present, without blocking."""
    token = get_token_from_request()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = int(payload["sub"])
        user = User.query.get(user_id)
        return user if user and user.is_active else None
    except Exception:
        return None


def get_or_restore_assistant(session_id: str, user_id: int | None = None) -> PatentAssistantEngine:
    """Retrieve or restore a PatentAssistantEngine. Rebuilds history from MySQL if server restarted."""
    with _sessions_lock:
        if session_id in _assistant_sessions:
            return _assistant_sessions[session_id]

        assistant = PatentAssistantEngine(top_k=4)

        # Restore history from MySQL if messages exist
        if user_id:
            try:
                db_messages = (
                    ChatMessage.query.filter_by(thread_id=session_id, user_id=user_id)
                    .order_by(ChatMessage.created_at.asc())
                    .all()
                )
                for msg in db_messages:
                    assistant.history.append({"role": msg.role, "content": msg.content})
                logger.info("Restored %d conversation turns for thread '%s' from MySQL", len(db_messages), session_id)
            except Exception as exc:
                logger.warning("Could not restore thread history from MySQL: %s", exc)

        _assistant_sessions[session_id] = assistant
        return assistant


# ------------------------------------------------------------------------------
# CORS Headers with Full Credential (HttpOnly Cookie) Support
# ------------------------------------------------------------------------------
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        origin = request.headers.get("Origin") or "http://localhost:5173"
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return response


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin") or "http://localhost:5173"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response


# ------------------------------------------------------------------------------
# Diagnostics & Health Endpoints
# ------------------------------------------------------------------------------
@app.get("/health")
def health():
    """Preserved system health check."""
    try:
        collection = get_or_create_collection()
        return jsonify({
            "status": "ok",
            "collection": collection.name,
            "chunks": collection.count()
        }), 200
    except Exception as exc:
        app.logger.exception("Health check failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.get("/api/collections/status")
def collections_status():
    """Detailed diagnostics of both pilot ChromaDB collections."""
    try:
        client = get_client()
        existing = {
            (c.name if hasattr(c, "name") else str(c)): c
            for c in client.list_collections()
        }

        target_collections = ["ip_sakti_ayush_v1", "ip_sakti_curcuma_test_v1"]
        coll_data = {}
        total_chunks = 0

        for name in target_collections:
            if name in existing:
                col = existing[name]
                count = col.count()
                total_chunks += count
                coll_data[name] = {
                    "count": count,
                    "available": True,
                    "metadata": col.metadata or {}
                }
            else:
                coll_data[name] = {
                    "count": 0,
                    "available": False,
                    "metadata": {}
                }

        return jsonify({
            "status": "ok",
            "total_chunks": total_chunks,
            "collections": coll_data
        }), 200
    except Exception as exc:
        app.logger.exception("Failed to query collection status")
        return jsonify({"status": "error", "message": str(exc)}), 500


# ------------------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/auth/register")
def auth_register():
    """Register a new researcher account."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    role = str(data.get("role", "researcher")).strip() or "researcher"

    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "A valid email address is required."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400

    if not full_name:
        return jsonify({"error": "Full name is required."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": f"An account with email '{email}' already exists."}), 409

    try:
        user = User(email=email, full_name=full_name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        token = create_access_token(user)
        resp = jsonify({
            "message": "Account created successfully.",
            "user": user.to_dict()
        })
        return set_auth_cookie(resp, token), 201
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Registration failed: %s", exc)
        return jsonify({"error": "Registration failed due to a server error."}), 500


@app.post("/api/auth/login")
def auth_login():
    """Authenticate researcher and issue secure HttpOnly JWT cookie."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    client_ip = request.remote_addr or "127.0.0.1"

    rate_key = f"{client_ip}_{email}"
    if is_rate_limited(rate_key):
        return jsonify({"error": "Too many failed login attempts. Please try again in 5 minutes."}), 429

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        record_failed_attempt(rate_key)
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        return jsonify({"error": "This account has been deactivated."}), 403

    clear_failed_attempts(rate_key)
    token = create_access_token(user)
    resp = jsonify({
        "message": "Login successful.",
        "user": user.to_dict()
    })
    return set_auth_cookie(resp, token), 200


@app.post("/api/auth/logout")
def auth_logout():
    """Log out user and invalidate cookie."""
    resp = jsonify({"message": "Logged out successfully."})
    return clear_auth_cookie(resp), 200


@app.get("/api/auth/me")
@login_required
def auth_me():
    """Get current authenticated researcher profile."""
    return jsonify({"user": g.current_user.to_dict()}), 200


# ------------------------------------------------------------------------------
# Innovation Projects & Versioned Claim Management Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/innovations")
@login_required
def list_innovations():
    """List all innovation projects owned by the authenticated researcher."""
    innovations = (
        Innovation.query.filter_by(user_id=g.current_user.id)
        .order_by(Innovation.updated_at.desc())
        .all()
    )
    return jsonify({
        "innovations": [i.to_dict(include_versions=False) for i in innovations]
    }), 200


@app.post("/api/innovations")
@login_required
def create_innovation():
    """Create a new innovation project and initialize Version 1."""
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "Innovation title is required."}), 400

    ayush_system = str(data.get("ayush_system", "Ayurveda")).strip() or "Ayurveda"
    problem = str(data.get("problem", "")).strip()
    solution = str(data.get("solution", "")).strip()
    claimed_advantages = str(data.get("claimed_advantages", "")).strip()

    raw_ingredients = data.get("ingredients") or []
    if not raw_ingredients or (isinstance(raw_ingredients, list) and not [x for x in raw_ingredients if str(x).strip()]):
        return jsonify({"error": "At least one ingredient or botanical substance is required."}), 400

    raw_features = data.get("technical_features") or []
    if not raw_features or (isinstance(raw_features, list) and not [x for x in raw_features if str(x).strip()]):
        return jsonify({"error": "At least one technical feature is required."}), 400

    document_ids = data.get("document_ids") or []

    try:
        innovation = Innovation(
            user_id=g.current_user.id,
            title=title,
            ayush_system=ayush_system,
            status="draft"
        )
        db.session.add(innovation)
        db.session.flush()

        v1 = InnovationVersion(
            innovation_id=innovation.id,
            version_number=1,
            title=title,
            ayush_system=ayush_system,
            problem=problem,
            solution=solution,
            ingredients=raw_ingredients,
            technical_features=raw_features,
            claimed_advantages=claimed_advantages,
            change_summary="Initial submission (Version 1)"
        )
        db.session.add(v1)
        db.session.flush()

        # Associate any uploaded applicant documents
        for doc_id in document_ids:
            doc = InnovationDocument.query.filter_by(id=doc_id, user_id=g.current_user.id).first()
            if doc:
                doc.innovation_id = innovation.id
                doc.version_id = v1.id

        db.session.commit()
        return jsonify({"innovation": innovation.to_dict(include_versions=True)}), 201

    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Failed to create innovation: %s", exc)
        return jsonify({"error": "Could not create innovation project."}), 500


@app.get("/api/innovations/<innovation_id>")
@login_required
def get_innovation(innovation_id: str):
    """Retrieve an innovation project and its immutable version history."""
    innovation = Innovation.query.filter_by(id=innovation_id, user_id=g.current_user.id).first()
    if not innovation:
        return jsonify({"error": "Innovation not found or unauthorized."}), 404

    return jsonify({"innovation": innovation.to_dict(include_versions=True)}), 200


@app.put("/api/innovations/<innovation_id>")
@login_required
def update_innovation(innovation_id: str):
    """Update innovation specifications by creating a NEW immutable version."""
    innovation = Innovation.query.filter_by(id=innovation_id, user_id=g.current_user.id).first()
    if not innovation:
        return jsonify({"error": "Innovation not found or unauthorized."}), 404

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip() or innovation.title
    ayush_system = str(data.get("ayush_system", "")).strip() or innovation.ayush_system
    problem = str(data.get("problem", "")).strip()
    solution = str(data.get("solution", "")).strip()
    claimed_advantages = str(data.get("claimed_advantages", "")).strip()
    change_summary = str(data.get("change_summary", "Updated innovation parameters")).strip()

    raw_ingredients = data.get("ingredients")
    raw_features = data.get("technical_features")
    latest = innovation.latest_version

    ingredients = raw_ingredients if raw_ingredients is not None else (latest.ingredients if latest else [])
    features = raw_features if raw_features is not None else (latest.technical_features if latest else [])

    if not ingredients:
        return jsonify({"error": "At least one ingredient is required."}), 400
    if not features:
        return jsonify({"error": "At least one technical feature is required."}), 400

    next_version_num = (latest.version_number + 1) if latest else 1

    try:
        new_version = InnovationVersion(
            innovation_id=innovation.id,
            version_number=next_version_num,
            title=title,
            ayush_system=ayush_system,
            problem=problem,
            solution=solution,
            ingredients=ingredients,
            technical_features=features,
            claimed_advantages=claimed_advantages,
            change_summary=change_summary
        )
        db.session.add(new_version)
        db.session.flush()

        # Update innovation parent metadata
        innovation.title = title
        innovation.ayush_system = ayush_system
        innovation.updated_at = datetime.utcnow()

        # Associate documents if passed
        document_ids = data.get("document_ids") or []
        for doc_id in document_ids:
            doc = InnovationDocument.query.filter_by(id=doc_id, user_id=g.current_user.id).first()
            if doc:
                doc.version_id = new_version.id

        db.session.commit()
        return jsonify({
            "message": f"Version {next_version_num} created successfully.",
            "innovation": innovation.to_dict(include_versions=True)
        }), 200

    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Failed to create new innovation version: %s", exc)
        return jsonify({"error": "Could not update innovation version."}), 500


@app.delete("/api/innovations/<innovation_id>")
@login_required
def delete_innovation(innovation_id: str):
    """Delete an innovation project and its associated versions and runs."""
    innovation = Innovation.query.filter_by(id=innovation_id, user_id=g.current_user.id).first()
    if not innovation:
        return jsonify({"error": "Innovation not found or unauthorized."}), 404

    try:
        db.session.delete(innovation)
        db.session.commit()
        return jsonify({"message": f"Innovation '{innovation_id}' deleted."}), 200
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Failed to delete innovation: %s", exc)
        return jsonify({"error": "Failed to delete innovation."}), 500


# ------------------------------------------------------------------------------
# Persistent Prior-Art Analysis Execution Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/innovations/<innovation_id>/analyze")
@login_required
def analyze_innovation_project(innovation_id: str):
    """Execute prior-art discovery on an innovation and persist an immutable AnalysisRun."""
    innovation = Innovation.query.filter_by(id=innovation_id, user_id=g.current_user.id).first()
    if not innovation:
        return jsonify({"error": "Innovation not found or unauthorized."}), 404

    latest_version = innovation.latest_version
    if not latest_version:
        return jsonify({"error": "Innovation has no version records to analyze."}), 400

    # Build engine payload from immutable version record
    payload = {
        "title": latest_version.title,
        "ayush_system": latest_version.ayush_system,
        "problem": latest_version.problem or "Not specified",
        "solution": latest_version.solution or "Not specified",
        "ingredients": latest_version.ingredients,
        "technical_features": latest_version.technical_features,
        "claimed_advantages": latest_version.claimed_advantages or "None specified",
        "uploaded_documents": [d.to_dict(include_full_text=True) for d in latest_version.documents]
    }

    # Count runs for this innovation to determine run number
    run_count = len(innovation.analysis_runs)
    run_number = run_count + 1

    run_record = AnalysisRun(
        innovation_id=innovation.id,
        version_id=latest_version.id,
        user_id=g.current_user.id,
        run_number=run_number,
        status="RUNNING"
    )
    db.session.add(run_record)
    db.session.commit()

    try:
        engine = get_innovation_engine()
        result = engine.analyze(payload)

        run_record.status = "COMPLETED"
        run_record.retrieval_status = result.get("retrieval_status", "COMPLETED")
        run_record.sources_count = result.get("sources_count", 0)
        run_record.queries_executed = result.get("queries_executed", [])
        run_record.citation_audit = result.get("citation_audit")
        run_record.report_markdown = result.get("report_markdown")
        run_record.report_json = result
        run_record.completed_at = datetime.utcnow()

        innovation.status = "analyzed"
        innovation.updated_at = datetime.utcnow()
        db.session.commit()

        result["run_id"] = run_record.id
        result["run_number"] = run_record.run_number
        return jsonify(result), 200

    except Exception as exc:
        app.logger.exception("Analysis execution failed for run %s: %s", run_record.id, exc)
        run_record.status = "FAILED"
        run_record.error_message = str(exc)
        run_record.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"error": f"Analysis execution failed: {str(exc)}", "run_id": run_record.id}), 500


@app.get("/api/innovations/<innovation_id>/runs")
@login_required
def get_innovation_runs(innovation_id: str):
    """Retrieve all persistent historical analysis runs for an innovation."""
    innovation = Innovation.query.filter_by(id=innovation_id, user_id=g.current_user.id).first()
    if not innovation:
        return jsonify({"error": "Innovation not found or unauthorized."}), 404

    runs = (
        AnalysisRun.query.filter_by(innovation_id=innovation_id, user_id=g.current_user.id)
        .order_by(AnalysisRun.run_number.desc())
        .all()
    )
    return jsonify({"runs": [r.to_dict(include_report=False) for r in runs]}), 200


@app.get("/api/innovations/<innovation_id>/runs/<run_id>")
@login_required
def get_specific_run(innovation_id: str, run_id: str):
    """Retrieve complete report markdown and audit of a specific persistent analysis run."""
    run_record = AnalysisRun.query.filter_by(id=run_id, innovation_id=innovation_id, user_id=g.current_user.id).first()
    if not run_record:
        return jsonify({"error": "Analysis run not found or unauthorized."}), 404

    return jsonify({"run": run_record.to_dict(include_report=True)}), 200


# Preserved single-turn analyze endpoint (backward compatible)
@app.post("/api/innovation/analyze")
def innovation_analyze():
    """Direct analysis endpoint supporting both authenticated and demo users."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; JSON object expected"}), 400

    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "Innovation title is required."}), 400

    raw_ingredients = data.get("ingredients")
    if not raw_ingredients:
        return jsonify({"error": "At least one ingredient or botanical substance is required."}), 400

    raw_features = data.get("technical_features")
    if not raw_features:
        return jsonify({"error": "At least one technical feature is required for prior-art comparison."}), 400

    try:
        engine = get_innovation_engine()
        result = engine.analyze(data)

        # If user is logged in, automatically persist as a project and run
        user = get_authenticated_user_from_request()
        if user:
            try:
                inn = Innovation(
                    user_id=user.id,
                    title=title,
                    ayush_system=str(data.get("ayush_system", "Ayurveda")),
                    status="analyzed"
                )
                db.session.add(inn)
                db.session.flush()

                v1 = InnovationVersion(
                    innovation_id=inn.id,
                    version_number=1,
                    title=title,
                    ayush_system=inn.ayush_system,
                    problem=data.get("problem", ""),
                    solution=data.get("solution", ""),
                    ingredients=raw_ingredients,
                    technical_features=raw_features,
                    claimed_advantages=data.get("claimed_advantages", ""),
                    change_summary="Analyzed submission"
                )
                db.session.add(v1)
                db.session.flush()

                run = AnalysisRun(
                    innovation_id=inn.id,
                    version_id=v1.id,
                    user_id=user.id,
                    run_number=1,
                    status="COMPLETED",
                    retrieval_status=result.get("retrieval_status"),
                    sources_count=result.get("sources_count", 0),
                    queries_executed=result.get("queries_executed"),
                    citation_audit=result.get("citation_audit"),
                    report_markdown=result.get("report_markdown"),
                    report_json=result,
                    completed_at=datetime.utcnow()
                )
                db.session.add(run)
                db.session.commit()
                result["innovation_id"] = inn.id
                result["run_id"] = run.id
            except Exception as e:
                db.session.rollback()
                logger.warning("Could not auto-persist analysis to user account: %s", e)

        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        app.logger.exception("Innovation analysis failed")
        return jsonify({"error": "Innovation analysis could not be completed. Check server logs."}), 500


# ------------------------------------------------------------------------------
# Document Upload and Deletion Endpoints with User Ownership
# ------------------------------------------------------------------------------
@app.post("/api/documents/upload")
def upload_document():
    """Secure multipart/form-data endpoint for innovation document extraction."""
    if "file" not in request.files and "files" not in request.files:
        return jsonify({"error": "No file uploaded. Expected multipart form field 'file' or 'files'."}), 400

    uploaded_files = request.files.getlist("files") or request.files.getlist("file")
    if not uploaded_files or not uploaded_files[0].filename:
        return jsonify({"error": "No file selected for upload."}), 400

    extractor = get_document_extractor()
    processed_results = []
    user = get_authenticated_user_from_request()

    for file_obj in uploaded_files:
        original_name = file_obj.filename or "uploaded_document"
        try:
            target_path, doc_id, stored_filename = extractor.save_uploaded_file(file_obj, original_name)
            extraction_result = extractor.extract(target_path, original_name, doc_id=doc_id)

            # Persist to MySQL if user is authenticated
            if user and extraction_result.get("status") in {"success", "warning"}:
                try:
                    db_doc = InnovationDocument(
                        id=doc_id,
                        user_id=user.id,
                        innovation_id="pending_assignment",
                        filename=original_name,
                        stored_filename=stored_filename,
                        file_type=extraction_result.get("file_type", "pdf"),
                        file_size=extraction_result.get("file_size", 0),
                        page_count=extraction_result.get("page_count", 1),
                        text_length=extraction_result.get("text_length", 0),
                        extracted_text=extraction_result.get("extracted_text", ""),
                        pages_json=extraction_result.get("pages", []),
                        metadata_json=extraction_result.get("metadata", {}),
                        warnings_json=extraction_result.get("warnings", [])
                    )
                    db.session.add(db_doc)
                    db.session.commit()
                except Exception as db_exc:
                    db.session.rollback()
                    logger.warning("Could not persist document metadata to MySQL: %s", db_exc)

            processed_results.append(extraction_result)

        except ValueError as ve:
            processed_results.append({
                "status": "error",
                "document_id": None,
                "filename": original_name,
                "file_size": 0,
                "error": str(ve),
                "warnings": [str(ve)]
            })
        except Exception as exc:
            app.logger.exception("Extraction failed for file %s", original_name)
            processed_results.append({
                "status": "error",
                "document_id": None,
                "filename": original_name,
                "file_size": 0,
                "error": f"Failed to process file: {str(exc)}",
                "warnings": ["Unexpected error during extraction."]
            })

    # Single-file upload response
    if len(processed_results) == 1:
        single = processed_results[0]
        if single.get("status") == "error" and single.get("document_id") is None:
            return jsonify(single), 400
        return jsonify(single), 200

    has_any_success = any(r.get("status") in {"success", "warning"} for r in processed_results)
    response_code = 200 if has_any_success else 400
    return jsonify({
        "status": "ok" if has_any_success else "error",
        "count": len(processed_results),
        "documents": processed_results
    }), response_code


@app.delete("/api/documents/<document_id>")
def delete_document(document_id: str):
    """Safely removes an uploaded applicant document from the sandbox and MySQL."""
    document_id = str(document_id).strip()
    if not document_id or not document_id.startswith("doc_"):
        return jsonify({"error": "Invalid document ID format."}), 400

    user = get_authenticated_user_from_request()
    if user:
        # Check ownership
        db_doc = InnovationDocument.query.filter_by(id=document_id).first()
        if db_doc and db_doc.user_id != user.id:
            return jsonify({"error": "Unauthorized to delete this document."}), 403
        if db_doc:
            db.session.delete(db_doc)
            db.session.commit()

    extractor = get_document_extractor()
    deleted = False
    for path in extractor.upload_dir.glob(f"{document_id}_*"):
        try:
            path.unlink(missing_ok=True)
            deleted = True
        except Exception as exc:
            app.logger.warning("Failed to delete file %s: %s", path, exc)

    return jsonify({
        "status": "ok",
        "message": f"Document '{document_id}' removed.",
        "deleted": deleted
    }), 200


# ------------------------------------------------------------------------------
# Persistent Conversational Patent Assistant Endpoints (MySQL Backed)
# ------------------------------------------------------------------------------
@app.get("/api/assistant/threads")
@login_required
def get_assistant_threads():
    """Retrieve all persistent research threads belonging to the authenticated researcher."""
    threads = (
        ChatThread.query.filter_by(user_id=g.current_user.id)
        .order_by(ChatThread.updated_at.desc())
        .all()
    )
    return jsonify({"threads": [t.to_dict(include_messages=False) for t in threads]}), 200


@app.post("/api/assistant/threads")
@login_required
def create_assistant_thread():
    """Explicitly create a new persistent research thread."""
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip() or None
    title = str(data.get("title", "New Research Thread")).strip()
    language = str(data.get("language", "English")).strip()

    thread = ChatThread(
        id=session_id or None,
        user_id=g.current_user.id,
        title=title,
        language=language
    )
    db.session.add(thread)
    db.session.commit()
    return jsonify({"thread": thread.to_dict(include_messages=False)}), 201


@app.get("/api/assistant/threads/<thread_id>")
@login_required
def get_assistant_thread(thread_id: str):
    """Retrieve conversation messages and cited evidence for a specific thread."""
    thread = ChatThread.query.filter_by(id=thread_id, user_id=g.current_user.id).first()
    if not thread:
        return jsonify({"error": "Research thread not found or unauthorized."}), 404

    return jsonify({"thread": thread.to_dict(include_messages=True)}), 200


@app.delete("/api/assistant/threads/<thread_id>")
@login_required
def delete_assistant_thread(thread_id: str):
    """Delete a research thread and its persistent dialogue turns."""
    thread = ChatThread.query.filter_by(id=thread_id, user_id=g.current_user.id).first()
    if not thread:
        return jsonify({"error": "Research thread not found or unauthorized."}), 404

    with _sessions_lock:
        _assistant_sessions.pop(thread_id, None)

    db.session.delete(thread)
    db.session.commit()
    return jsonify({"message": f"Thread '{thread_id}' deleted."}), 200


@app.post("/api/assistant/chat")
def assistant_chat():
    """Multi-turn conversational patent research with persistent MySQL storage."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; JSON object expected"}), 400

    session_id = str(data.get("session_id", "")).strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    query_text = str(data.get("query", "")).strip()
    if not query_text:
        return jsonify({"error": "query is required"}), 400

    language = str(data.get("language", "English")).strip() or "English"
    filters = data.get("filters")
    if filters is not None and not isinstance(filters, dict):
        return jsonify({"error": "filters must be a JSON object if provided"}), 400

    user = get_authenticated_user_from_request()
    user_id = user.id if user else None

    # Enforce thread isolation if thread is already registered to a user
    thread = None
    if user:
        thread = ChatThread.query.filter_by(id=session_id).first()
        if thread and thread.user_id != user.id:
            return jsonify({"error": "Unauthorized: This research thread belongs to another user."}), 403
        if not thread:
            # Create persistent thread
            short_title = query_text[:35] + ("..." if len(query_text) > 35 else "")
            thread = ChatThread(
                id=session_id,
                user_id=user.id,
                title=short_title,
                language=language
            )
            db.session.add(thread)
            db.session.commit()

    try:
        assistant = get_or_restore_assistant(session_id, user_id=user_id)
        result = assistant.ask(query_text, user_language=language, filters=filters)

        category = result.get("category", "AYUSH_RESEARCH")
        resolved_query = result.get("resolved_query", query_text)
        standalone_query = result.get("standalone_query", query_text)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        citation_audit = result.get("citation_audit")
        effective_language = result.get("language", language)

        # Persist conversation turns and cited evidence in MySQL
        if user and thread:
            try:
                # 1. User turn
                user_msg = ChatMessage(
                    thread_id=thread.id,
                    user_id=user.id,
                    role="user",
                    content=query_text
                )
                db.session.add(user_msg)
                db.session.flush()

                # 2. Assistant turn
                ast_msg = ChatMessage(
                    thread_id=thread.id,
                    user_id=user.id,
                    role="assistant",
                    content=answer,
                    category=category,
                    standalone_query=standalone_query,
                    resolved_query=resolved_query,
                    citation_audit=citation_audit
                )
                db.session.add(ast_msg)
                db.session.flush()

                # 3. Grounded source citations
                for src in sources:
                    src_record = ChatMessageSource(
                        message_id=ast_msg.id,
                        source_title=src.get("source") or "Document",
                        collection=src.get("collection") or "ip_sakti_ayush_v1",
                        document_type=src.get("document_type") or "other",
                        page=str(src.get("page") or "N/A"),
                        section=src.get("section") or "body",
                        chunk_id=str(src.get("id") or "chunk"),
                        rrf_score=src.get("rrf_score"),
                        evidence_text=src.get("evidence") or src.get("text") or ""
                    )
                    db.session.add(src_record)

                thread.language = effective_language
                thread.updated_at = datetime.utcnow()
                db.session.commit()
            except Exception as db_err:
                db.session.rollback()
                logger.warning("Failed to persist chat turns to MySQL: %s", db_err)

        response_payload = {
            "session_id": session_id,
            "answer": answer,
            "category": category,
            "standalone_query": standalone_query,
            "resolved_query": resolved_query,
            "sources": sources,
            "citation_audit": citation_audit,
            "language": effective_language
        }
        return jsonify(response_payload), 200

    except Exception:
        app.logger.exception("Assistant request failed for session %s", session_id)
        return jsonify({"error": "Assistant request failed. Check server logs."}), 500


@app.post("/api/assistant/reset")
def assistant_reset():
    """Reset the conversation history for a specific session."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; JSON object expected"}), 400

    session_id = str(data.get("session_id", "")).strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    with _sessions_lock:
        if session_id in _assistant_sessions:
            _assistant_sessions[session_id].reset_conversation()

    # Clear messages in MySQL if user owns thread
    user = get_authenticated_user_from_request()
    if user:
        try:
            thread = ChatThread.query.filter_by(id=session_id, user_id=user.id).first()
            if thread:
                ChatMessage.query.filter_by(thread_id=thread.id).delete()
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("Failed to clear MySQL messages on reset: %s", e)

    return jsonify({
        "status": "ok",
        "message": f"Conversation history for session '{session_id}' has been reset.",
        "session_id": session_id
    }), 200


# Preserved legacy single query
@app.post("/api/query")
def query_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body; JSON object expected"}), 400

    question = str(data.get("query", "")).strip()
    if not question:
        return jsonify({"error": "query is required"}), 400

    language = str(data.get("language", "English")).strip() or "English"
    valid_langs = {"english", "hindi", "telugu", "en", "hi", "te"}
    if language.lower() not in valid_langs:
        return jsonify({"error": f"Unsupported language '{language}'. Supported languages are English, Hindi, and Telugu."}), 400

    try:
        result = get_pipeline().run(question, user_language=language)
        return jsonify(result), 200
    except Exception as exc:
        app.logger.exception("RAG request failed: %s", exc)
        return jsonify({"error": "Request failed."}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
