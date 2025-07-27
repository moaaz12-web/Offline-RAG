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
    Get comprehensive schema information from Weaviate database including
    collections, properties, indexes, vectorizers, and sample data.
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
        

        schema_data = {
            "database_info": {
                "url": weaviate_url,
                "grpc_port": grpc_port,
                "total_collections": len(collections_config)
            },
            "collections": []
        }

        for collection_name, collection_config in collections_config.items():
            try:
                collection_instance = client.collections.get(collection_name)
                
                # Get collection statistics
                count_result = collection_instance.aggregate.over_all(total_count=True)
                total_count = count_result.total_count if count_result else 0

                # Extract detailed property information
                properties = []
                for prop in collection_config.properties:
                    property_info = {
                        "name": prop.name,
                        "data_type": str(prop.data_type.value) if prop.data_type else None,
                        "description": prop.description,
                        "index_filterable": prop.index_filterable,
                        "index_searchable": prop.index_searchable,
                        "index_range_filters": prop.index_range_filters,
                        "tokenization": str(prop.tokenization.value) if prop.tokenization else None,
                        "vectorizer": prop.vectorizer,
                        "vectorizer_config": str(prop.vectorizer_config) if prop.vectorizer_config else None
                    }
                    properties.append(property_info)

                # Get sample objects with all properties
                sample_results = collection_instance.query.fetch_objects(limit=5)
                sample_documents = []
                
                for obj in sample_results.objects:
                    # Extract all properties from the object
                    obj_data = {
                        "id": str(obj.uuid),
                        "properties": {}
                    }
                    
                    # Method 1: Try to access properties directly from obj.properties
                    if hasattr(obj, 'properties') and obj.properties:
                        for prop in collection_config.properties:
                            prop_name = prop.name
                            # Try different ways to access the property value
                            prop_value = None
                            
                            # Try direct attribute access
                            if hasattr(obj.properties, prop_name):
                                prop_value = getattr(obj.properties, prop_name)
                            # Try dictionary-style access
                            elif hasattr(obj.properties, '__dict__') and prop_name in obj.properties.__dict__:
                                prop_value = obj.properties.__dict__[prop_name]
                            # Try if properties is dict-like
                            elif hasattr(obj.properties, '__getitem__'):
                                try:
                                    prop_value = obj.properties[prop_name]
                                except (KeyError, TypeError):
                                    pass
                            
                            # Truncate long text fields for readability
                            if isinstance(prop_value, str) and len(prop_value) > 200:
                                prop_value = prop_value
                            
                            obj_data["properties"][prop_name] = prop_value
                    else:
                        # If obj.properties doesn't work, try accessing from obj directly
                        logger.warning(f"Could not access properties for object {obj.uuid}, trying alternative method")
                        for prop in collection_config.properties:
                            prop_name = prop.name
                            try:
                                # Try accessing directly from the object
                                if hasattr(obj, prop_name):
                                    prop_value = getattr(obj, prop_name)
                                elif hasattr(obj, '__dict__') and prop_name in obj.__dict__:
                                    prop_value = obj.__dict__[prop_name]
                                else:
                                    prop_value = None
                                
                                # Truncate long text fields for readability
                                if isinstance(prop_value, str) and len(prop_value) > 200:
                                    prop_value = prop_value[:200] + "..."
                                
                                obj_data["properties"][prop_name] = prop_value
                            except Exception as e:
                                logger.warning(f"Could not extract property {prop_name}: {e}")
                                obj_data["properties"][prop_name] = None
                    
                    sample_documents.append(obj_data)

                # Extract vectorizer and vector configuration
                vectorizer_info = {
                    "vectorizer": str(collection_config.vectorizer.value) if collection_config.vectorizer else "none",
                    "vectorizer_config": str(collection_config.vectorizer_config) if collection_config.vectorizer_config else None,
                    "vector_config": str(collection_config.vector_config) if collection_config.vector_config else None,
                    "reranker_config": str(collection_config.reranker_config) if collection_config.reranker_config else None,
                    "generative_config": str(collection_config.generative_config) if collection_config.generative_config else None
                }

                # Extract references/cross-references
                references = []
                if hasattr(collection_config, 'references') and collection_config.references:
                    for ref in collection_config.references:
                        references.append({
                            "name": getattr(ref, 'name', 'unknown'),
                            "target": getattr(ref, 'target', 'unknown'),
                            "description": getattr(ref, 'description', None)
                        })

                collection_schema = {
                    "collection_name": collection_name,
                    "description": collection_config.description,
                    "document_count": total_count,
                    "properties": properties,
                    "vectorizer_info": vectorizer_info,
                    "references": references,
                    "sample_documents": sample_documents,
                    "statistics": {
                        "total_properties": len(properties),
                        "searchable_properties": len([p for p in properties if p["index_searchable"]]),
                        "filterable_properties": len([p for p in properties if p["index_filterable"]]),
                        "sample_count": len(sample_documents)
                    }
                }

                schema_data["collections"].append(collection_schema)
                
                logger.info(f"Processed collection '{collection_name}': {total_count} documents, {len(properties)} properties")

            except Exception as e:
                logger.error(f"Error processing collection '{collection_name}': {str(e)}")
                # Add basic info even if detailed extraction fails
                error_collection = {
                    "collection_name": collection_name,
                    "error": str(e),
                    "document_count": 0,
                    "properties": [],
                    "sample_documents": []
                }
                schema_data["collections"].append(error_collection)

        client.close()
        
        # Add summary statistics
        schema_data["summary"] = {
            "total_documents": sum(c.get("document_count", 0) for c in schema_data["collections"]),
            "total_properties": sum(len(c.get("properties", [])) for c in schema_data["collections"]),
            "collections_with_vectors": len([c for c in schema_data["collections"] 
                                           if c.get("vectorizer_info", {}).get("vectorizer", "none") != "none"])
        }

        return schema_data

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
