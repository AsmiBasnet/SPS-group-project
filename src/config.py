# ================================================
# PolicyGuard Configuration
# All settings in one place — change here only
# ================================================

# Ollama settings
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen3.5:4b"
EMBED_MODEL = "nomic-embed-text"

# RAG settings
SIMILARITY_THRESHOLD = 0.65
TOP_K_CHUNKS = 3
CHUNK_SIZE = 400        # words per chunk
CHUNK_OVERLAP = 50      # overlap between chunks

# LLM settings
MAX_TOKENS = 300
CONTEXT_SIZE = 2048
TEMPERATURE = 0

# Session settings
SESSION_TIMEOUT_MINUTES = 30

# Database
DB_PATH = "logs/policygard.db"

# Supported documents
SUPPORTED_POLICIES = [
    "FMLA",
    "Harassment",
    "Vacation & Sick Leave",
    "ADA",
    "Absenteeism & Tardiness",    # ← updated
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