"""Central configuration for IP-SAKTI Sahayak."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PROJECT_NAME = os.getenv("PROJECT_NAME", "IP-SAKTI Sahayak")
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data" / "documents")))
VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", str(BASE_DIR / "vector_store_ip_sakti")))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ip_sakti_ayush_v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "6"))
RETRIEVAL_CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "30"))
ENABLE_OCR = os.getenv("ENABLE_OCR", "false").lower() in {"1", "true", "yes"}
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "eng+hin+tel")
SUPPORTED_LANGUAGES = {"en", "hi", "te"}

# MySQL 8 Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ip_sakti_sahayak")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")

# JWT & Authentication Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ipsakti-jwt-auth-secret-key-2026-ayush-grounded")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRES_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_DAYS", "7"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"true", "1", "yes"}
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

# Never point this project at the old NASA vector_store directory.
