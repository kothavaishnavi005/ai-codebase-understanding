import os
import threading
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - Django - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

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


# ====== VIEWS ======

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'rag_app/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'rag_app/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    # fallback for GET, though POST is preferred
    logout(request)
    return redirect('login')


@login_required
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
            logger.error(f"Error during chat streaming: {e}", exc_info=True)
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

@csrf_exempt
@require_POST
def api_explain_code(request):
    """Explain a provided code snippet."""
    try:
        data = json.loads(request.body)
        code = data.get("code")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
        
    if not code:
        return JsonResponse({"detail": "Code cannot be empty"}, status=400)
        
    engine = get_rag_engine()
    
    def generate():
        try:
            for chunk in engine.stream_explain_code(code):
                yield chunk
        except Exception as e:
            logger.error(f"Error during explain-code streaming: {e}", exc_info=True)
            yield f"\n\nError: {str(e)}"

    return StreamingHttpResponse(generate(), content_type='text/plain')
def api_status(request):
    """Get the current system and vector DB status."""
    engine = get_rag_engine()
    stats = engine.get_stats()
    
    return JsonResponse({
        "indexing_status": ingest_status,
        "database_stats": stats
    })
