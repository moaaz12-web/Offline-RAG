import re
from datetime import datetime
from typing import Optional

def extract_metadata_from_filename(filename: str) -> dict:
    """Extract metadata from filename in format '<doc_id>__v<version>__<effective_date>.extension'

    Example: SOP_Extrusion__v3__2023-01-01.pdf

    Returns:
        dict: Contains doc_id, version, effective_date, and source
    """
    # Remove file extension
    base_name = filename.rsplit('.', 1)[0]

    # Multiple robust patterns to handle various formats
    patterns = [
        # Standard format: doc_id__v<version>__YYYY-MM-DD
        r'^(.+?)__v(.+?)__(\d{4}-\d{2}-\d{2})$',
        # Alternative format: doc_id__v<version>__YYYY_MM_DD
        r'^(.+?)__v(.+?)__(\d{4}_\d{2}_\d{2})$',
        # Alternative format: doc_id_v<version>_YYYY-MM-DD (single underscore)
        r'^(.+?)_v(.+?)_(\d{4}-\d{2}-\d{2})$',
        # Alternative format: doc_id_v<version>_YYYY_MM_DD
        r'^(.+?)_v(.+?)_(\d{4}_\d{2}_\d{2})$',
        # Format without version: doc_id__YYYY-MM-DD
        r'^(.+?)__(\d{4}-\d{2}-\d{2})$',
        # Format without version: doc_id_YYYY-MM-DD
        r'^(.+?)_(\d{4}-\d{2}-\d{2})$',
    ]

    # Try each pattern
    for i, pattern in enumerate(patterns):
        match = re.match(pattern, base_name)
        if match:
            groups = match.groups()

            if len(groups) == 3:  # doc_id, version, date
                doc_id, version, effective_date = groups
                # Normalize date format (replace underscores with hyphens)
                effective_date = effective_date.replace('_', '-')
            elif len(groups) == 2:  # doc_id, date (no version)
                doc_id, effective_date = groups
                version = "unknown"
                # Normalize date format
                effective_date = effective_date.replace('_', '-')

            return {
                "doc_id": doc_id.strip(),
                "version": version.strip(),
                "effective_date": effective_date,
                "source": filename
            }

    # Additional fallback patterns for partial matches
    fallback_patterns = [
        # Just version pattern: anything with v<number>
        r'.*v(\d+(?:\.\d+)?).*',
        # Date pattern anywhere in filename: YYYY-MM-DD or YYYY_MM_DD
        r'.*(\d{4}[-_]\d{2}[-_]\d{2}).*',
    ]

    doc_id = base_name
    version = "unknown"
    effective_date = datetime.now().strftime("%Y-%m-%d")

    # Try to extract version if present
    for pattern in [r'.*v(\d+(?:\.\d+)?).*', r'.*version[_\s]*(\d+(?:\.\d+)?).*']:
        match = re.search(pattern, base_name, re.IGNORECASE)
        if match:
            version = f"v{match.group(1)}"
            break

    # Try to extract date if present
    date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', base_name)
    if date_match:
        effective_date = date_match.group(1).replace('_', '-')

    # Clean up doc_id by removing version and date parts
    clean_doc_id = base_name
    # Remove version patterns
    clean_doc_id = re.sub(r'[_\s]*v\d+(?:\.\d+)?[_\s]*', '', clean_doc_id, flags=re.IGNORECASE)
    clean_doc_id = re.sub(r'[_\s]*version[_\s]*\d+(?:\.\d+)?[_\s]*', '', clean_doc_id, flags=re.IGNORECASE)
    # Remove date patterns
    clean_doc_id = re.sub(r'[_\s]*\d{4}[-_]\d{2}[-_]\d{2}[_\s]*', '', clean_doc_id)
    # Clean up multiple underscores and trailing/leading underscores
    clean_doc_id = re.sub(r'_{2,}', '_', clean_doc_id).strip('_')

    if clean_doc_id:
        doc_id = clean_doc_id

    return {
        "doc_id": doc_id,
        "version": version,
        "effective_date": effective_date,
        "source": filename
    }


def get_all_metadata_from_weaviate() -> dict:
    """
    Retrieve all unique metadata values from Weaviate database
    to help with intelligent metadata inference during retrieval.

    Returns:
        dict: Contains lists of unique doc_ids, versions, effective_dates, and sources
    """
    weaviate_url = "http://weaviate:8080"
    grpc_port = int(os.environ.get("WEAVIATE_GRPC_PORT", 50051))

    try:
        client = WeaviateClient(
            connection_params=ConnectionParams.from_url(weaviate_url, grpc_port=grpc_port)
        )
        client.connect()

        # Get the DocumentIndex collection
        collection = client.collections.get("DocumentIndex")

        # Query all documents to get metadata
        results = collection.query.fetch_objects(
            limit=1000,  # Adjust based on your dataset size
            return_properties=["doc_id", "version", "effective_date", "source"]
        )
        logger.info(results)

        # Extract unique values
        doc_ids = set()
        versions = set()
        effective_dates = set()
        sources = set()

        for obj in results.objects:
            props = getattr(obj, "properties", {})
            if not isinstance(props, dict):
                continue
            if "doc_id" in props and props["doc_id"]:
                doc_ids.add(props["doc_id"])
            if "version" in props and props["version"]:
                versions.add(props["version"])
            if "effective_date" in props and props["effective_date"]:
                effective_dates.add(props["effective_date"])
            if "source" in props and props["source"]:
                sources.add(props["source"])

        client.close()

        return {
            "doc_ids": sorted(list(doc_ids)),
            "versions": sorted(list(versions)),
            "effective_dates": sorted(list(effective_dates)),
            "sources": sorted(list(sources)),
            "total_documents": len(results.objects)
        }

    except Exception as e:
        logger.error(f"Error retrieving metadata from Weaviate: {str(e)}")
        return {
            "doc_ids": [],
            "versions": [],
            "effective_dates": [],
            "sources": [],
            "total_documents": 0,
            "error": str(e)
        }
    

    
import weaviate
import os
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient
from logger import logger

import weaviate
import os
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient
from logger import logger
from typing import Dict, List, Any, Optional

import weaviate
import os
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient
from logger import logger
from typing import Dict, List, Any, Optional

def get_weaviate_structure():
    """
    Get clean summary of Weaviate database showing unique document metadata combinations per index.
    Returns only essential information: index names and unique combinations of doc_id, version, effective_date.
    """
    weaviate_url = "http://weaviate:8080"
    grpc_port = int(os.environ.get("WEAVIATE_GRPC_PORT", 50051))

    try:
        client = WeaviateClient(
            connection_params=ConnectionParams.from_url(weaviate_url, grpc_port=grpc_port)
        )
        client.connect()

        # Get all collection configurations
        collections_config = client.collections.list_all()
        summary_data = {
            "indexes": []
        }

        for collection_name, collection_config in collections_config.items():
            try:
                collection_instance = client.collections.get(collection_name)
                # Get total count
                count_result = collection_instance.aggregate.over_all(total_count=True)
                total_count = count_result.total_count if count_result else 0

                # Get unique combinations of doc_id, version, effective_date
                unique_combinations = []
                if total_count > 0:
                    try:
                        # Query all documents to get unique metadata combinations
                        all_results = collection_instance.query.fetch_objects(
                            limit=1000,  # Adjust based on your dataset size
                            return_properties=["doc_id", "version", "effective_date"]
                        )

                        # Track unique combinations
                        unique_combos_set = set()

                        for obj in all_results.objects:
                            # Extract metadata safely
                            doc_id = None
                            version = None
                            effective_date = None

                            if hasattr(obj, 'properties') and obj.properties:
                                # Try to get properties
                                for prop_name in ["doc_id", "version", "effective_date"]:
                                    try:
                                        if hasattr(obj.properties, prop_name):
                                            value = getattr(obj.properties, prop_name)
                                        elif hasattr(obj.properties, '__dict__') and prop_name in obj.properties.__dict__:
                                            value = obj.properties.__dict__[prop_name]
                                        elif hasattr(obj.properties, '__getitem__'):
                                            try:
                                                value = obj.properties[prop_name]
                                            except (KeyError, TypeError):
                                                value = None
                                        else:
                                            value = None

                                        if prop_name == "doc_id":
                                            doc_id = value
                                        elif prop_name == "version":
                                            version = value
                                        elif prop_name == "effective_date":
                                            effective_date = value

                                    except Exception as e:
                                        logger.warning(f"Could not extract {prop_name}: {e}")

                            # Create combination tuple (using "unknown" for missing values)
                            combination = (
                                doc_id or "unknown",
                                version or "unknown",
                                effective_date or "unknown"
                            )
                            unique_combos_set.add(combination)

                        # Convert to list of dictionaries for JSON response
                        for doc_id, version, effective_date in sorted(unique_combos_set):
                            unique_combinations.append({
                                "doc_id": doc_id,
                                "version": version,
                                "effective_date": effective_date
                            })

                    except Exception as e:
                        logger.warning(f"Could not extract unique combinations for {collection_name}: {e}")

                # Create simple index info
                index_info = {
                    "index_name": collection_name,
                    "total_documents": total_count,
                    "unique_combinations": unique_combinations,
                    "unique_count": len(unique_combinations)
                }

                summary_data["indexes"].append(index_info)
                
                logger.info(f"Processed index '{collection_name}': {total_count} documents, {len(unique_combinations)} unique combinations")

            except Exception as e:
                logger.error(f"Error processing collection '{collection_name}': {str(e)}")
                # Add error info for this collection
                summary_data["indexes"].append({
                    "index_name": collection_name,
                    "error": str(e),
                    "total_documents": 0,
                    "unique_combinations": []
                })

        client.close()
        return summary_data

    except Exception as e:
        logger.error(f"Failed to connect to Weaviate or extract schema: {str(e)}")
        return {
            "error": str(e),
            "database_info": {
                "url": weaviate_url,
                "grpc_port": grpc_port
            },
            "collections": []
        }
