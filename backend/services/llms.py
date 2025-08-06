import os
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_embedding_model = None

# Path inside container where the model will be saved and reused
LOCAL_MODEL_PATH = "/app/local_models/paraphrase-multilingual-MiniLM-L12-v2"

def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        logger.info("Loading multilingual embedding model...")

        # Step 1: Check if local model exists
        if os.path.exists(LOCAL_MODEL_PATH):
            logger.info(f"📁 Found cached model at {LOCAL_MODEL_PATH}, loading from local path...")
            model_name_or_path = LOCAL_MODEL_PATH
        else:
            logger.info("⬇️ No local model found. Downloading from Hugging Face and caching...")
            model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            os.makedirs(os.path.dirname(LOCAL_MODEL_PATH), exist_ok=True)
            model.save(LOCAL_MODEL_PATH)
            model_name_or_path = LOCAL_MODEL_PATH

        # Step 2: Load using Langchain wrapper
        try:
            _embedding_model = HuggingFaceEmbeddings(
                model_name=model_name_or_path,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ Embedding model loaded successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            raise

    return _embedding_model

# Proxy class to keep code compatible
class EmbeddingModelProxy:
    def __getattr__(self, name):
        return getattr(get_embedding_model(), name)

    def embed_documents(self, texts):
        return get_embedding_model().embed_documents(texts)

    def embed_query(self, text):
        return get_embedding_model().embed_query(text)

HFEmbeddings = EmbeddingModelProxy()

def preload_embedding_model():
    logger.info("Preloading embedding model...")
    get_embedding_model()
    logger.info("Embedding model preloaded successfully!")



# LLM configuration
from langchain_ollama import ChatOllama

ollama_model = ChatOllama(model=os.getenv("OLLAMA_MODEL"), base_url="http://ollama:11434")
llm = ollama_model
