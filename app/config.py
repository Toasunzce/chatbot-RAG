import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "ai-forever/ru-en-RoSBERTa"

QDRANT_PATH = "./data/qdrant"
COLLECTION = "docs"

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 5
MAX_HISTORY = 20