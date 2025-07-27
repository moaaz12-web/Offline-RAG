from langchain_core.prompts import ChatPromptTemplate
from .llms import HFEmbeddings, llm
from utils import get_all_metadata_from_weaviate
from logger import logger
from schemas import QueryMetadata, MetadataInference

class ModelService:
    def __init__(self):
        self.llm = llm
        self.embeddings = HFEmbeddings
        # Create structured output LLMs for different schemas
        self.metadata_llm = llm.with_structured_output(MetadataInference)
        self.query_metadata_llm = llm.with_structured_output(QueryMetadata)

    def extract_metadata(self, query: str) -> dict:
        """
        Legacy method for backward compatibility.
        Now calls the intelligent metadata inference method.
        """
        return self.infer_metadata_from_query(query)

    def infer_metadata_from_query(self, query: str) -> dict:
        """
        Intelligently infer metadata from user query by first retrieving
        all available metadata from the database and then using LLM to
        find the best matches.
        """
        try:
            # Get all available metadata from the database
            available_metadata = get_all_metadata_from_weaviate()
            
            # Use LLM to intelligently match query to available metadata
            return self._llm_metadata_inference(query, available_metadata)

        except Exception as e:
            # Fallback to simple extraction on any error
            logger.error(f"Error inferring metadata: {str(e)}")
            return None

    def _llm_metadata_inference(self, query: str, available_metadata: dict) -> dict:
        """
        Use LLM to intelligently infer the best metadata matches from available options.
        """
        logger.info(f"Available metadata: {available_metadata}")
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert at matching user queries to document metadata. "
             "Given a user query and available metadata from a document database, "
             "identify the most relevant doc_id, version, and effective_date.\n\n"
             "Available metadata in the database:\n"
             f"Document IDs: {available_metadata.get('doc_ids', [])}\n"
             f"Versions: {available_metadata.get('versions', [])}\n"
             f"Effective Dates: {available_metadata.get('effective_dates', [])}\n\n"
             "Rules:\n"
             "1. If the query mentions specific document names, procedures, or topics, match to the most relevant doc_id\n"
             "2. If the query mentions version numbers (v1, v2, version 3, etc.), match to the closest available version\n"
             "3. If the query mentions dates or time periods, match to the most relevant effective_date\n"
             "4. If no clear match exists, use 'unknown' for that field\n"
             "5. Assess your confidence level in the matches (high/medium/low)\n"
             "6. Provide brief reasoning for your choices\n\n"
             "**IMPORTANT**: Only use values from the available options above, or 'unknown' if no good match exists."
            ),
            ("human", "User query: {query}\n\nPlease identify the most relevant metadata with confidence and reasoning:")
        ])

        try:
            chain = prompt | self.metadata_llm
            response = chain.invoke({"query": query})

            logger.info(f"Structured metadata response: {response}")

            # Convert structured response to dict format expected by the rest of the system
            return {
                "doc_id": response.doc_id,
                "version": response.version,
                "effective_date": response.effective_date
            }

        except Exception as e:
            logger.error(f"Error in structured metadata inference: {str(e)}")

    def _extract_from_llm_response(self, response_text: str, available_metadata: dict) -> dict:
        """
        Extract metadata from LLM response using pattern matching as fallback.
        """
        doc_id = "unknown"
        version = "unknown"
        effective_date = "unknown"

        # Try to find doc_id matches in the response
        for available_doc_id in available_metadata.get('doc_ids', []):
            if available_doc_id.lower() in response_text.lower():
                doc_id = available_doc_id
                break

        # Try to find version matches
        for available_version in available_metadata.get('versions', []):
            if available_version.lower() in response_text.lower():
                version = available_version
                break

        # Try to find date matches
        for available_date in available_metadata.get('effective_dates', []):
            if available_date in response_text:
                effective_date = available_date
                break

        return {
            "doc_id": doc_id,
            "version": version,
            "effective_date": effective_date
        }

    def _simple_metadata_extraction(self, query: str) -> dict:
        """
        Simple fallback metadata extraction using basic patterns.
        """
        import re

        # Simple pattern matching for fallback
        doc_id = "unknown"
        version = "unknown"
        effective_date = "unknown"

        # Look for version patterns
        version_match = re.search(r'v(\d+(?:\.\d+)?)', query, re.IGNORECASE)
        if version_match:
            version = f"v{version_match.group(1)}"

        # Look for date patterns
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
        if date_match:
            effective_date = date_match.group(1)

        # Look for common document types
        doc_patterns = [
            r'sop[_\s]*(\w+)',
            r'procedure[_\s]*(\w+)',
            r'manual[_\s]*(\w+)',
            r'guide[_\s]*(\w+)',
            r'policy[_\s]*(\w+)'
        ]

        for pattern in doc_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                doc_id = f"{match.group(0).replace(' ', '_')}"
                break

        return {
            "doc_id": doc_id,
            "version": version,
            "effective_date": effective_date
        }