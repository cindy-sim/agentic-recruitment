import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Email monitoring settings
EMAIL_CHECK_INTERVAL = 20 # seconds
HR_EMAIL = "cindysim@arxmedia.co"  # HR manager's email address to filter out

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLASSIFICATION_MODEL = "gpt-3.5-turbo"  # For email classification
ANALYSIS_MODEL = "gpt-4o"  # For detailed resume analysis

# Tavily API settings
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Gmail API settings
GMAIL_CREDENTIALS_FILE = os.path.join(BASE_DIR, "client_secret_320464042133-dmj6qqj1kgagn1566589pi5pl2fqoo3h.apps.googleusercontent.com.json")
GMAIL_TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# PDF processing settings
POPPLER_PATH = r'C:\Users\USER\poppler-24.08.0\Library\bin'  # Path to poppler binaries for PDF conversion

# Data storage
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_EMAILS_FILE = os.path.join(DATA_DIR, "processed_emails.json")
CONVERSATION_CACHE_DIR = os.path.join(DATA_DIR, "conversation_cache")
BACKGROUND_CHECKS_DIR = os.path.join(DATA_DIR, "background_checks")

# Logging
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_LEVEL = "INFO"

# Temporary directory for storing converted images
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Directory for storing converted attachment images
ATTACHMENT_IMAGES_DIR = os.path.join(BASE_DIR, "data", "attachment_images")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONVERSATION_CACHE_DIR, exist_ok=True)
os.makedirs(BACKGROUND_CHECKS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(ATTACHMENT_IMAGES_DIR, exist_ok=True)