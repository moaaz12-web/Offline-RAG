# tasks.py

from services.splitter import TextSplitterService
from utils import extract_metadata_from_filename
from logger import logger

from langchain_weaviate.vectorstores import WeaviateVectorStore
from dotenv import load_dotenv
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
import os
from services.llms import HFEmbeddings

load_dotenv()

def ingest_document_sync(file_path: str, original_filename: str):
    logger.info(f"Starting document ingestion for: {original_filename}")

    import time
    ingest_start = time.time()

    try:
        splitter = TextSplitterService()

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
        elif ext in ['.doc', '.docx']:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
        elif ext == '.txt':
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
        else:
            logger.error(f"Unsupported file type: {ext}")
            raise ValueError(f"Unsupported file type: {ext}")

        documents = loader.load()

        split_docs = splitter.split_documents(documents)

        metadata = extract_metadata_from_filename(original_filename)
        logger.info(f"Extracted metadata from document: {metadata}")

        for doc in split_docs:
            doc.metadata.update(metadata)

        weaviate_url = "http://weaviate:8080"

        client = WeaviateClient(
            connection_params=ConnectionParams.from_url(weaviate_url, grpc_port=50051)
        )
        client.connect()
        logger.info("Connected to Weaviate successfully")

        embedding = HFEmbeddings

        # Store in Weaviate
        logger.info("💾 Storing documents in Weaviate vector database...")
        store_start = time.time()

        WeaviateVectorStore.from_documents(
            documents=split_docs,
            embedding=embedding,
            client=client,
            index_name="DocumentIndex",  # change as needed
            text_key="content",
        )

        store_time = time.time() - store_start
        ingest_total_time = time.time() - ingest_start

        os.remove(file_path)

        logger.info(f"Document ingestion completed successfully in {ingest_total_time:.2f}s")

        return {"status": "success", "document_count": len(split_docs)}

    except Exception as e:
        ingest_total_time = time.time() - ingest_start
        logger.error(f"Document ingestion failed: {str(e)}")
        logger.exception(f"Full error traceback for {original_filename}:")

        # Clean up temporary file if it still exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Failed to clean up temporary file: {cleanup_error}")

        raise
