import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = str(DATA_DIR / "newsverify.db")
FAISS_INDEX_PATH = str(DATA_DIR / "faiss_index.bin")
FAISS_METADATA_PATH = str(DATA_DIR / "faiss_metadata.json")

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS = {
    "primary": "deepseek/deepseek-chat",
    "fallback_1": "qwen/qwen-2-7b-instruct",
    "fallback_2": "google/gemma-2-9b-it",
}

SUPPORTED_YEARS = {2025, 2026}

SIMILARITY_THRESHOLD = 0.60
TOP_K = 5

RSS_SOURCES = {
    "Google News Top": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "Google News Technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Google News Sports": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Google News Business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Google News Science": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Google News World": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlhkU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "The Hindu": "https://www.thehindu.com/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/feed/",
}

CLUSTER_THRESHOLD = 0.55
