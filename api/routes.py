import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Import RAG engine and ingestion logic
from rag.engine import get_rag_engine
from rag.ingest import process_codebase

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

router = APIRouter()

# Global state for ingestion tracking
ingest_status = {
    "is_indexing": False,
    "last_error": None,
    "last_success": None,
}

class IndexRequest(BaseModel):
    # Absolute or relative path to the directory to index
    # We will expand it to absolute path
    path: str
    
class ChatRequest(BaseModel):
    question: str

class ExplainCodeRequest(BaseModel):
    code: str

def run_indexing_task(target_path: str):
    """Background task to process and index documents."""
    global ingest_status
    ingest_status["is_indexing"] = True
    ingest_status["last_error"] = None
    ingest_status["last_success"] = None
    
    try:
        # Get absolute path and strip surrounding quotes
        target_path = target_path.strip('\'"')
        abs_path = os.path.abspath(target_path)
        if not os.path.exists(abs_path):
            raise Exception(f"Path does not exist: {abs_path}")
            
        logger.info(f"Starting background index for {abs_path}")
        
        # Parse and chunk documents
        chunks = process_codebase(abs_path)
        
        # Get engine and initialize DB with new documents
        engine = get_rag_engine()
        # For simplicity, we clear the DB entirely to index the single target codebase each time
        engine.clear_database()
        
        # Add to ChromaDB
        engine.add_documents(chunks)
        
        logger.info(f"Successfully indexed {len(chunks)} document chunks.")
        ingest_status["last_success"] = f"Indexed {len(chunks)} chunks from {abs_path}"
    except Exception as e:
        logger.error(f"Error during indexing task: {e}", exc_info=True)
        ingest_status["last_error"] = str(e)
    finally:
        ingest_status["is_indexing"] = False

@router.post("/ingest")
async def ingest_codebase(request: IndexRequest, background_tasks: BackgroundTasks):
    """Trigger background ingestion of a codebase directory."""
    if ingest_status["is_indexing"]:
        raise HTTPException(status_code=400, detail="An indexing task is already running.")
        
    path = request.path
    if not path:
        raise HTTPException(status_code=400, detail="Path must be provided")
        
    # Start the parsing and embedding task in the background
    background_tasks.add_task(run_indexing_task, path)
    
    return {"message": "Indexing started in background.", "path": request.path}

@router.post("/chat")
def chat_with_codebase(request: ChatRequest):
    """Ask a question to the senior engineer AI about the codebase."""
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
        
    # Standard check
    engine = get_rag_engine()
    stats = engine.get_stats()
    
    # Check if there are documents in the DB
    if stats.get("document_chunks", 0) == 0:
        return {
            "answer": "I don't have any codebase indexed yet. Please ingest a directory first using the ingestion tool.",
            "source_chunks_found": 0
        }
        
    try:
        # Get response from the RAG chain
        answer = engine.query(request.question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error during chain invocation: {e}", exc_info=True)
        # One common error implies missing OPENAI_API_KEY
        if "api key" in str(e).lower():
            raise HTTPException(status_code=500, detail="LLM Provider API Key missing or invalid.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/explain-code")
def explain_code_endpoint(request: ExplainCodeRequest):
    """Explain a provided code snippet."""
    if not request.code:
        logger.warning("Rejecting explain-code request with empty snippet")
        raise HTTPException(status_code=400, detail="Code cannot be empty")
        
    engine = get_rag_engine()
    try:
        answer = engine.explain_code(request.code)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error during explain-code chain invocation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status():
    """Get the current system and vector DB status."""
    engine = get_rag_engine()
    stats = engine.get_stats()
    
    return {
        "indexing_status": ingest_status,
        "database_stats": stats
    }
