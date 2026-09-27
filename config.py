import os
from dotenv import load_dotenv


# Load variables from .env during local development
load_dotenv()


# Base project directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --------------------------------------------------
    # Flask Security
    # --------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY")

    # --------------------------------------------------
    # Database Configuration
    # --------------------------------------------------
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Compatibility for some PostgreSQL database URLs
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = (
        DATABASE_URL
        if DATABASE_URL
        else f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'vivamate.db')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --------------------------------------------------
    # Upload Configuration
    # --------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # Maximum upload size: 10 MB
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Allowed VivaMate file types
    ALLOWED_EXTENSIONS = {
        "pdf",
        "txt",
        "py"
    }

    # --------------------------------------------------
    # Gemini AI Configuration
    # --------------------------------------------------
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        ""
    ).strip()