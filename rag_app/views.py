import os
import threading
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json

# Import RAG engine and ingestion logic (assuming rag folder is in project root)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.engine import get_rag_engine
from rag.ingest import process_codebase

# Global state for ingestion tracking
ingest_status = {
    "is_indexing": False,
    "last_error": None,
    "last_success": None,
}

def run_indexing_task(target_path: str):
    """Background task to process and index documents."""
    global ingest_status
    ingest_status["is_indexing"] = True
    ingest_status["last_error"] = None
    
    try:
        # Get absolute path and strip surrounding quotes
        target_path = target_path.strip('\'"')
        abs_path = os.path.abspath(target_path)
        if not os.path.exists(abs_path):
            raise Exception(f"Path does not exist: {abs_path}")
            
        print(f"Starting background index for {abs_path}")
        
        # Parse and chunk documents
        chunks = process_codebase(abs_path)
        
        # Get engine and initialize DB with new documents
        engine = get_rag_engine()
        engine.clear_database()
        
        # Add to ChromaDB
        engine.add_documents(chunks)
        
        print(f"Successfully indexed {len(chunks)} document chunks.")
        ingest_status["last_success"] = f"Indexed {len(chunks)} chunks from {abs_path}"
    except Exception as e:
        print(f"Error during indexing task: {e}")
        ingest_status["last_error"] = str(e)
    finally:
        ingest_status["is_indexing"] = False


# ====== VIEWS ======

def index_view(request):
    """Render the main SPA frontend view."""
    return render(request, "rag_app/index.html")

@csrf_exempt
@require_POST
def api_ingest(request):
    """Trigger background ingestion of a codebase directory."""
    global ingest_status
    if ingest_status["is_indexing"]:
        return JsonResponse({"detail": "An indexing task is already running."}, status=400)
        
    try:
        data = json.loads(request.body)
        path = data.get("path")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON mapping"}, status=400)
        
    if not path:
        return JsonResponse({"detail": "Path must be provided"}, status=400)
        
    # Start the parsing and embedding task in the background thread
    thread = threading.Thread(target=run_indexing_task, args=(path,))
    thread.daemon = True
    thread.start()
    
    return JsonResponse({"message": "Indexing started in background.", "path": path})

@csrf_exempt
@require_POST
def api_chat(request):
    """Ask a question to the senior engineer AI about the codebase."""
    try:
        data = json.loads(request.body)
        question = data.get("question")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
        
    if not question:
        return JsonResponse({"detail": "Question cannot be empty"}, status=400)
        
    engine = get_rag_engine()
    stats = engine.get_stats()
    
    if stats.get("document_chunks", 0) == 0:
        return JsonResponse({
            "answer": "I don't have any codebase indexed yet. Please ingest a directory first using the ingestion tool.",
            "source_chunks_found": 0
        })
        
    def generate():
        try:
            for chunk in engine.stream(question):
                yield chunk
        except Exception as e:
            print(f"Error during chain streaming: {e}")
            yield f"\n\nError: {str(e)}"

    return StreamingHttpResponse(generate(), content_type='text/plain')

@require_GET
def api_status(request):
    """Get the current system and vector DB status."""
    engine = get_rag_engine()
    stats = engine.get_stats()
    
    return JsonResponse({
        "indexing_status": ingest_status,
        "database_stats": stats
    })
