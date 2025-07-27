from langchain.schema import BaseRetriever, Document
from typing import List
from weaviate.classes.query import Filter
from logger import logger

class CustomWeaviateRetriever(BaseRetriever):
    def __init__(self, vector_store, metadata_filters=None, k=5, alpha=0.5):
        super().__init__()  # initialize BaseRetriever
        self._vector_store = vector_store
        self._metadata_filters = metadata_filters or []
        self._k = k
        self._alpha = alpha

    def get_relevant_documents(self, query: str) -> List[Document]:
        combined_filter = None
        logger.info(f"Metadata filters type: {type(self._metadata_filters)}")
        logger.info(f"Metadata filters value: {self._metadata_filters}")

        if self._metadata_filters:
            # Handle both single Filter object and list of Filter objects
            if isinstance(self._metadata_filters, list):
                # If it's a list, combine them
                combined_filter = self._metadata_filters[0]
                for f in self._metadata_filters[1:]:
                    combined_filter &= f
            else:
                # If it's already a single Filter object, use it directly
                combined_filter = self._metadata_filters

        return self._vector_store.similarity_search(
            query=query,
            filters=combined_filter,
            k=self._k,
            alpha=self._alpha
        )
