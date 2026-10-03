# CodeAI - Codebase Understanding System

## Deployment Guide (Render & Cloud)

This project has been updated for cloud deployment using FastAPI, Django, LangChain, and Google Gemini.

### 1. Environment Variables
The application requires the following environment variables to function correctly in production:
* `GEMINI_API_KEY`: Your Google Gemini API Key. (The application will fail gracefully if this is missing).

**Note:** Never commit `.env` or hardcode your API key.

### 2. Build Command
For Render, use the following build command to install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Start Command
Use the following production-safe Uvicorn command to start the application. Render automatically provides the `$PORT` environment variable.
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 4. Vector Database Initialization
The `db/` folder containing the Chroma vector database is intentionally excluded from Git. 
When the application starts, it will automatically detect if the database is empty. If it is, the application runs a background process to parse, chunk, and index the current codebase automatically.

### 5. Testing the Deployed Application
Once deployed, you can verify it is running by:
1. Navigating to the root url (`/`) to ensure the frontend loads.
2. Checking the health endpoint: `/health` (should return `{"status": "ok", "message": "API is running"}`).
3. Testing a casual query ("Hi") or asking an architectural question to verify Gemini is responding successfully.
