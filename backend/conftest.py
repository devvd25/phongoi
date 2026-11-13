"""Keep every pytest collection path isolated from the live SQLite database."""

import os


os.environ["DATABASE_URL"] = "sqlite:///./test_phongoi.db"
os.environ["LLM_PROVIDER"] = "none"

