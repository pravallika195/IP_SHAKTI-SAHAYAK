"""SQLAlchemy Models for IP-SAKTI Sahayak.

Tables:
1. users — Authenticated researcher identities & credentials.
2. innovations — Research projects / patent discovery workspaces.
3. innovation_versions — Immutable version history of submitted claims.
4. innovation_documents — Sandboxed applicant-attached files & extracted disclosures.
5. analysis_runs — Persistent prior-art evaluation runs & audit records.
6. chat_threads — Conversational Patent Assistant research sessions.
7. chat_messages — Multi-turn dialogue messages with resolved queries & audits.
8. chat_message_sources — Grounded passage evidence attached to assistant turns.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

import bcrypt
from database import db


def generate_uuid() -> str:
    return uuid.uuid4().hex


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="researcher", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    innovations = db.relationship("Innovation", back_populates="user", cascade="all, delete-orphan", lazy="select")
    chat_threads = db.relationship("ChatThread", back_populates="user", cascade="all, delete-orphan", lazy="select")

    def set_password(self, password: str):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Innovation(db.Model):
    __tablename__ = "innovations"
    __table_args__ = (
        db.Index("idx_innovations_user_updated", "user_id", "updated_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    ayush_system = db.Column(db.String(100), default="Ayurveda", nullable=False)
    status = db.Column(db.String(50), default="draft", nullable=False)  # 'draft', 'analyzed', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="innovations")
    versions = db.relationship("InnovationVersion", back_populates="innovation", cascade="all, delete-orphan", order_by="InnovationVersion.version_number.desc()")
    documents = db.relationship("InnovationDocument", back_populates="innovation", cascade="all, delete-orphan")
    analysis_runs = db.relationship("AnalysisRun", back_populates="innovation", cascade="all, delete-orphan", order_by="AnalysisRun.run_number.desc()")

    @property
    def latest_version(self) -> InnovationVersion | None:
        return self.versions[0] if self.versions else None

    def to_dict(self, include_versions: bool = False) -> dict[str, Any]:
        latest = self.latest_version
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "ayush_system": self.ayush_system,
            "status": self.status,
            "latest_version_number": latest.version_number if latest else 1,
            "latest_version": latest.to_dict() if latest else None,
            "versions_count": len(self.versions),
            "runs_count": len(self.analysis_runs),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_versions:
            data["versions"] = [v.to_dict() for v in self.versions]
            data["analysis_runs"] = [r.to_dict(include_report=False) for r in self.analysis_runs]
        return data


class InnovationVersion(db.Model):
    __tablename__ = "innovation_versions"
    __table_args__ = (
        db.UniqueConstraint("innovation_id", "version_number", name="uq_innovation_version"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    innovation_id = db.Column(db.String(36), db.ForeignKey("innovations.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(500), nullable=False)
    ayush_system = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.JSON, nullable=False)  # Array of string or structured ingredient items
    technical_features = db.Column(db.JSON, nullable=False)  # Array of strings
    claimed_advantages = db.Column(db.Text, nullable=True)
    change_summary = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    innovation = db.relationship("Innovation", back_populates="versions")
    documents = db.relationship("InnovationDocument", back_populates="version")
    analysis_runs = db.relationship("AnalysisRun", back_populates="version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "innovation_id": self.innovation_id,
            "version_number": self.version_number,
            "title": self.title,
            "ayush_system": self.ayush_system,
            "problem": self.problem,
            "solution": self.solution,
            "ingredients": self.ingredients or [],
            "technical_features": self.technical_features or [],
            "claimed_advantages": self.claimed_advantages,
            "change_summary": self.change_summary,
            "documents": [d.to_dict() for d in self.documents],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InnovationDocument(db.Model):
    __tablename__ = "innovation_documents"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    innovation_id = db.Column(db.String(36), db.ForeignKey("innovations.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = db.Column(db.String(36), db.ForeignKey("innovation_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, default=1, nullable=False)
    text_length = db.Column(db.Integer, default=0, nullable=False)
    extracted_text = db.Column(db.Text(length=4294967295), nullable=True)  # MySQL LONGTEXT
    pages_json = db.Column(db.JSON, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    warnings_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    innovation = db.relationship("Innovation", back_populates="documents")
    version = db.relationship("InnovationVersion", back_populates="documents")

    def to_dict(self, include_full_text: bool = False) -> dict[str, Any]:
        data = {
            "id": self.id,
            "document_id": self.id,
            "innovation_id": self.innovation_id,
            "version_id": self.version_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "text_length": self.text_length,
            "metadata": self.metadata_json or {},
            "warnings": self.warnings_json or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_full_text:
            data["extracted_text"] = self.extracted_text
            data["pages"] = self.pages_json or []
        return data


class AnalysisRun(db.Model):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        db.UniqueConstraint("innovation_id", "run_number", name="uq_innovation_run"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    innovation_id = db.Column(db.String(36), db.ForeignKey("innovations.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = db.Column(db.String(36), db.ForeignKey("innovation_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="COMPLETED", nullable=False)  # 'RUNNING', 'COMPLETED', 'FAILED'
    retrieval_status = db.Column(db.String(50), nullable=True)
    sources_count = db.Column(db.Integer, default=0, nullable=False)
    queries_executed = db.Column(db.JSON, nullable=True)
    citation_audit = db.Column(db.JSON, nullable=True)
    report_markdown = db.Column(db.Text(length=4294967295), nullable=True)  # MySQL LONGTEXT
    report_json = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    innovation = db.relationship("Innovation", back_populates="analysis_runs")
    version = db.relationship("InnovationVersion", back_populates="analysis_runs")

    def to_dict(self, include_report: bool = True) -> dict[str, Any]:
        data = {
            "id": self.id,
            "run_id": self.id,
            "innovation_id": self.innovation_id,
            "version_id": self.version_id,
            "run_number": self.run_number,
            "status": self.status,
            "retrieval_status": self.retrieval_status,
            "sources_count": self.sources_count,
            "queries_executed": self.queries_executed or [],
            "citation_audit": self.citation_audit,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_report:
            data["report_markdown"] = self.report_markdown
            data["report_json"] = self.report_json
        return data


class ChatThread(db.Model):
    __tablename__ = "chat_threads"
    __table_args__ = (
        db.Index("idx_chat_threads_user_updated", "user_id", "updated_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    language = db.Column(db.String(50), default="English", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="chat_threads")
    messages = db.relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at.asc()")

    def to_dict(self, include_messages: bool = False) -> dict[str, Any]:
        data = {
            "id": self.id,
            "session_id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "language": self.language,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (
        db.Index("idx_chat_messages_thread_time", "thread_id", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    thread_id = db.Column(db.String(36), db.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'user', 'assistant'
    content = db.Column(db.Text(length=4294967295), nullable=False)
    category = db.Column(db.String(50), nullable=True)  # 'GREETING', 'AYUSH_RESEARCH', 'FOLLOW_UP', 'OUT_OF_DOMAIN'
    standalone_query = db.Column(db.Text, nullable=True)
    resolved_query = db.Column(db.Text, nullable=True)
    citation_audit = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    thread = db.relationship("ChatThread", back_populates="messages")
    sources = db.relationship("ChatMessageSource", back_populates="message", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "category": self.category,
            "standalone_query": self.standalone_query,
            "resolved_query": self.resolved_query,
            "citation_audit": self.citation_audit,
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChatMessageSource(db.Model):
    __tablename__ = "chat_message_sources"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    message_id = db.Column(db.String(36), db.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    source_title = db.Column(db.String(500), nullable=False)
    collection = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(100), nullable=True)
    page = db.Column(db.String(50), nullable=True)
    section = db.Column(db.String(100), nullable=True)
    chunk_id = db.Column(db.String(150), nullable=False)
    rrf_score = db.Column(db.Float, nullable=True)
    evidence_text = db.Column(db.Text(length=16777215), nullable=False)  # MEDIUMTEXT
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = db.relationship("ChatMessage", back_populates="sources")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source_title,
            "collection": self.collection,
            "document_type": self.document_type,
            "page": self.page,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "rrf_score": self.rrf_score,
            "evidence": self.evidence_text,
            "text": self.evidence_text,
        }

