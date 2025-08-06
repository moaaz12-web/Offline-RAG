from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import time
from typing import List, Optional
from contextlib import asynccontextmanager
from tasks import ingest_document_sync
from services.model import ModelService
from services.crag import CRAGService
from services.llms import preload_embedding_model
from dotenv import load_dotenv
from utils import get_weaviate_structure
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from logger import logger

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting RAG application initialization...")
    logger.info("📋 Initializing components:")
    logger.info("   - FastAPI server")
    logger.info("   - Model services")
    logger.info("   - CRAG workflow")
    logger.info("   - Embedding model (multilingual)")

    startup_start = time.time()

    # Preload the embedding model to avoid delays on first request
    try:
        logger.info("🔄 Step 1/1: Preloading embedding model...")
        preload_embedding_model()
        logger.info("✅ Embedding model preloaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to preload embedding model: {e}")
        logger.warning("⚠️ Application will continue, but first request will be slower")
        # Don't fail startup, but log the error

    startup_time = time.time() - startup_start
    logger.info(f"🎉 RAG application startup completed in {startup_time:.2f} seconds!")
    logger.info("🌐 Server is ready to accept requests")
    logger.info("📚 Endpoints available:")
    logger.info("   - POST /ingest - Upload documents")
    logger.info("   - POST /query - Ask questions")
    logger.info("   - GET /inspect - View database structure")
    logger.info("   - DELETE /clear - Clear indexes")
    logger.info("   - GET /logs - View recent application logs")

    yield  # Application is running

    # Shutdown (if needed)
    logger.info("🛑 RAG application shutting down...")
    logger.info("👋 Goodbye!")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_service = ModelService()
crag_service = CRAGService()

class QueryRequest(BaseModel):
    query: str

class ClearIndexRequest(BaseModel):
    index_name: Optional[str] = None  # If None, clears all indexes

@app.post("/ingest")
async def ingest(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    file_infos = []

    for file in files:
        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}_{file.filename}"
        logger.info(f"Processing file: {file.filename} (size: {file.size if hasattr(file, 'size') else 'unknown'} bytes)")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        background_tasks.add_task(ingest_document_sync, file_path, file.filename)
        file_infos.append({"filename": file.filename, "status": "processing"})

    return JSONResponse(content={"message": "Processing started", "files": file_infos}, status_code=202)

@app.post("/query")
def query(query_request: QueryRequest):
    query_text = query_request.query

    query_start = time.time()
    
    logList = []
    logList.append("Step 1: Inferring metadata from query")

    # Intelligently infer metadata from query using available database metadata
    logger.info("🔍 Inferring metadata from query...")
    try:
        metadata = model_service.infer_metadata_from_query(query_text)
        logList.append(f"Metadata inferred is: {metadata}")
    except Exception as e:
        logger.info("Error inferring metadata, using fallback metadata values")
        # Fallback to default values
        metadata = {
            "doc_id": "unknown",
            "version": "unknown",
            "effective_date": "unknown"
        }
        logList.append("Fallback metadata used: {metadata}")

    logList.append("\n")
    logList.append("Step 2: Running C-RAG workflow")

    # Run C-RAG workflow with inferred metadata
    logger.info("🤖 Running C-RAG workflow...")
    crag_start = time.time()
    result = crag_service.run(query_text, metadata)
    crag_time = time.time() - crag_start

    query_total_time = time.time() - query_start

    logList.extend(result.get("logs", []))

    logger.info(f"Query processed successfully in {query_total_time:.2f}s (C-RAG: {crag_time:.2f}s)")

    return {
        "answer": result["generation"],
        "metadata_used": metadata,
        "sources": result.get("documents", []),
        "logs": logList
    }

@app.get("/inspect")
def inspect_weaviate():
    try:
        structure = get_weaviate_structure()
        return {"collections": structure}
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to inspect Weaviate: {str(e)}"}
        )

@app.delete("/clear")
def clear_weaviate_index(request: ClearIndexRequest):
    
    target = request.index_name if request.index_name else "ALL"

    clear_start = time.time()

    try:
        weaviate_url = "http://weaviate:8080"
        grpc_port = int(os.environ.get("WEAVIATE_GRPC_PORT", 50051))

        client = WeaviateClient(
            connection_params=ConnectionParams.from_url(weaviate_url, grpc_port=grpc_port)
        )
        client.connect()

        cleared_collections = []
        errors = []

        if request.index_name:
            # Clear specific index/collection
            try:
                if client.collections.exists(request.index_name):
                    # Get document count before deletion
                    collection = client.collections.get(request.index_name)
                    count_result = collection.aggregate.over_all(total_count=True)
                    doc_count = count_result.total_count if count_result else 0

                    # Delete the collection
                    client.collections.delete(request.index_name)
                    cleared_collections.append({
                        "name": request.index_name,
                        "documents_deleted": doc_count,
                        "status": "success"
                    })
                    logger.info(f"Successfully cleared collection '{request.index_name}' with {doc_count} documents")
                else:
                    errors.append(f"Collection '{request.index_name}' does not exist")
                    logger.warning(f"Attempted to clear non-existent collection: {request.index_name}")

            except Exception as e:
                error_msg = f"Failed to clear collection '{request.index_name}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        else:
            # Clear ALL collections
            try:
                collections_config = client.collections.list_all()
                logger.info(f"Found {len(collections_config)} collections to clear")

                for collection_name in collections_config.keys():
                    try:
                        # Get document count before deletion
                        collection = client.collections.get(collection_name)
                        count_result = collection.aggregate.over_all(total_count=True)
                        doc_count = count_result.total_count if count_result else 0

                        # Delete the collection
                        client.collections.delete(collection_name)
                        cleared_collections.append({
                            "name": collection_name,
                            "documents_deleted": doc_count,
                            "status": "success"
                        })
                        logger.info(f"Successfully cleared collection '{collection_name}' with {doc_count} documents")

                    except Exception as e:
                        error_msg = f"Failed to clear collection '{collection_name}': {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                error_msg = f"Failed to list collections: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        client.close()

        # Prepare response
        total_documents_deleted = sum(col["documents_deleted"] for col in cleared_collections)

        response_data = {
            "operation": "clear_index",
            "target": request.index_name if request.index_name else "ALL",
            "cleared_collections": cleared_collections,
            "total_collections_cleared": len(cleared_collections),
            "total_documents_deleted": total_documents_deleted,
            "errors": errors,
            "success": len(errors) == 0
        }

        clear_time = time.time() - clear_start

        if errors:
            logger.warning(f"⚠️ Clear operation completed with {len(errors)} errors in {clear_time:.2f}s")
            logger.warning(f"📊 Partial success: {len(cleared_collections)} collections cleared, {total_documents_deleted} documents deleted")
            return JSONResponse(
                status_code=207,  # Multi-Status (partial success)
                content=response_data
            )
        else:
            logger.info(f"✅ Clear operation completed successfully in {clear_time:.2f}s")
            logger.info(f"📊 Results: {len(cleared_collections)} collections cleared, {total_documents_deleted} documents deleted")
            return JSONResponse(
                status_code=200,
                content=response_data
            )

    except Exception as e:
        clear_time = time.time() - clear_start
        error_msg = f"Failed to connect to Weaviate or perform clear operation: {str(e)}"
        logger.error(f"❌ Clear operation failed after {clear_time:.2f}s: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={
                "operation": "clear_index",
                "target": request.index_name if request.index_name else "ALL",
                "error": error_msg,
                "success": False
            }
        )

@app.get("/logs")
def get_recent_logs(lines: int = 50):
    """
    Get recent log entries from the application log file.

    Args:
        lines: Number of recent log lines to return (default: 50, max: 500)

    Returns:
        JSON response with recent log entries
    """
    try:
        # Limit the number of lines to prevent excessive data transfer
        lines = min(max(lines, 1), 500)

        log_file_path = os.path.join("storage", "logs", "app.log")

        if not os.path.exists(log_file_path):
            return JSONResponse(
                status_code=404,
                content={"error": "Log file not found", "logs": []}
            )

        # Read the last N lines from the log file
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Parse log entries and return structured data
        log_entries = []
        for line in recent_lines:
            line = line.strip()
            if line:
                log_entries.append({
                    "timestamp": line[:19] if len(line) > 19 else "",
                    "level": "",
                    "message": line,
                    "raw": line
                })

                # Try to extract log level if it follows the standard format
                if "] [" in line and line.startswith("["):
                    try:
                        parts = line.split("] [", 2)
                        if len(parts) >= 3:
                            log_entries[-1]["level"] = parts[1]
                            log_entries[-1]["message"] = parts[2].split(": ", 1)[-1] if ": " in parts[2] else parts[2]
                    except:
                        pass  # Keep the original message if parsing fails

        return {
            "logs": log_entries,
            "total_lines": len(log_entries),
            "requested_lines": lines
        }

    except Exception as e:
        logger.error(f"Failed to read log file: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to read logs: {str(e)}", "logs": []}
        )