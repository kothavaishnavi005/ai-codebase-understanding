import os
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(
    title="Senior Engineer Simulator",
    description="AI-powered Codebase Understanding System API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include API routers
from api.routes import router as api_router
from api.routes import run_indexing_task
from rag.engine import get_rag_engine
import threading

app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Check if the vector database is empty and index if necessary."""
    try:
        engine = get_rag_engine()
        stats = engine.get_stats()
        if stats.get("document_chunks", 0) == 0:
            print("Database is empty. Starting background indexing of current directory...")
            # Run in a background thread to avoid blocking startup
            project_dir = os.path.dirname(os.path.abspath(__file__))
            threading.Thread(target=run_indexing_task, args=(project_dir,)).start()
        else:
            print(f"Database already contains {stats.get('document_chunks')} chunks. Skipping initial indexing.")
    except Exception as e:
        print(f"Error during startup indexing check: {e}")

# Serve static files from the "static" directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health")
async def health():
    """Health check endpoint for cloud deployment."""
    return {"status": "ok", "message": "API is running"}

# Setup Django WSGI
import os
import django
from fastapi.middleware.wsgi import WSGIMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "code_ai.settings")
django.setup()
from django.core.wsgi import get_wsgi_application
django_app = get_wsgi_application()

app.mount("/", WSGIMiddleware(django_app))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

