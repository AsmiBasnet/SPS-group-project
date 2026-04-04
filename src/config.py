# ================================================
# PolicyGuard Configuration
# All settings loaded from .env — change there only
# ================================================

import os
from dotenv import load_dotenv

load_dotenv()

# Ollama settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME  = os.getenv("MODEL_NAME",  "qwen3.5:4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# RAG settings
SIMILARITY_THRESHOLD = 0.65
TOP_K_CHUNKS = 2        # reduced from 3 — less context sent to LLM
CHUNK_SIZE   = 300      # reduced from 400 — smaller chunks, fewer input tokens
CHUNK_OVERLAP = 50      # overlap between chunks

# LLM settings
MAX_TOKENS   = 150      # reduced from 300 — JSON response never needs more
CONTEXT_SIZE = 1024
TEMPERATURE  = 0

# Session settings
SESSION_TIMEOUT_MINUTES = 30

# Database
DB_PATH = os.getenv("DB_PATH", "logs/policygard.db")

# Admin
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Supported documents
SUPPORTED_POLICIES = [
    "FMLA",
    "Harassment",
    "Vacation & Sick Leave",
    "ADA",
    "Absenteeism & Tardiness",
    "Other"
]

# Employee types
EMPLOYEE_TYPES = [
    "-- Select --",
    "Full-time Regular",
    "Part-time Regular",
    "Probationary",
    "Contractor",
    "Temporary"
]

# Issue categories
ISSUE_CATEGORIES = [
    "-- Select --",
    "FMLA / Medical Leave",
    "Harassment / Discrimination",
    "Vacation / Sick Leave",
    "ADA Accommodation",
    "Absenteeism & Tardiness",
    "Termination",
    "Notice Period",
    "Disciplinary",
    "Other"
]
