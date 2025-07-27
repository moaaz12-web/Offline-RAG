from weaviate.classes.query import Filter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder


from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
import os
from dotenv import load_dotenv
from logger import logger
load_dotenv()

from .custom_retriever import CustomWeaviateRetriever
from .llms import HFEmbeddings

from langchain_weaviate.vectorstores import WeaviateVectorStore

def retrieval_pipeline(state):
    # Setup client and embedding
    weaviate_url = "http://weaviate:8080"
    grpc_port = int(os.environ.get("WEAVIATE_GRPC_PORT", 50051))
    client = WeaviateClient(
        connection_params=ConnectionParams.from_url(weaviate_url, grpc_port=grpc_port)
    )
    client.connect()

    try:
        # Use multilingual embedding model that supports Spanish and English
        embedding = HFEmbeddings

        # Create vector store instance
        vector_store = WeaviateVectorStore(
            client=client,
            index_name="DocumentIndex",  # make sure this matches your ingest code
            text_key="content",          # matches your Document content field
            embedding=embedding
        )

        # Build metadata filters based on inferred metadata
        metadata_filters = None
        metadata = state.get("metadata", {})

        if metadata:
            filters = []

            # Add filters for non-unknown values
            if metadata.get("doc_id") and metadata["doc_id"] != "unknown":
                filters.append(Filter.by_property("doc_id").equal(metadata["doc_id"]))
                logger.info(f"Filtering by doc_id: {metadata['doc_id']}")

            if metadata.get("version") and metadata["version"] != "unknown":
                filters.append(Filter.by_property("version").equal(metadata["version"]))
                logger.info(f"Filtering by version: {metadata['version']}")

            if metadata.get("effective_date") and metadata["effective_date"] != "unknown":
                filters.append(Filter.by_property("effective_date").equal(metadata["effective_date"]))
                logger.info(f"Filtering by effective_date: {metadata['effective_date']}")

            # Combine filters with AND logic
            if filters:
                metadata_filters = filters[0]
                for filter_item in filters[1:]:
                    metadata_filters = metadata_filters & filter_item

        # Initialize custom retriever with metadata filters
        retriever = CustomWeaviateRetriever(
            vector_store,
            metadata_filters=metadata_filters,
            k=5,
            alpha=0.7
        )

        # Setup reranker
        model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        reranker = CrossEncoderReranker(model=model)

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=reranker,
            base_retriever=retriever
        )

        # Get reranked results
        results = compression_retriever.get_relevant_documents(state["query"])

        logger.info(f"Retrieved {len(results)} documents after filtering and reranking")

        # Convert results to string format for the CRAG workflow
        documents_text = []
        for doc in results:
            # Include metadata information in the document text
            doc_info = f"Document: {doc.page_content}"
            if hasattr(doc, 'metadata') and doc.metadata:
                doc_info += f"\nMetadata: {doc.metadata}"
            documents_text.append(doc_info)

        return {"documents": "\n\n".join(documents_text)}

    finally:
        client.close()