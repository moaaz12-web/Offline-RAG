# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# model.save("./local_models/paraphrase-multilingual-MiniLM-L12-v2")

from langchain_huggingface import HuggingFaceEmbeddings

_embedding_model = HuggingFaceEmbeddings(
    model_name="./local_models/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},  # Explicitly set to CPU
    encode_kwargs={'normalize_embeddings': True}  # Normalize for better similarity calculations
)