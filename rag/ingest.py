import os
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Common extensions to index
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css", ".md", ".txt", ".json", 
    ".java", ".cpp", ".c", ".h", ".hpp", ".go", ".rs", ".rb", ".php"
}

# Directories to ignore
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", "env", ".env", 
    "build", "dist", ".idea", ".vscode", "coverage"
}

def load_documents_from_path(root_path: str) -> List[Document]:
    """Traverse directory and load all supported code files."""
    documents = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        
        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_path = os.path.join(dirpath, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        # Only index non-empty files
                        if content.strip():
                            doc = Document(
                                page_content=content,
                                metadata={"source": file_path, "filename": file, "extension": ext}
                            )
                            documents.append(doc)
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    
    return documents

def chunk_documents(documents: List[Document]) -> List[Document]:
    """Chunk code documents into smaller pieces for vector storage."""
    # Using RecursiveCharacterTextSplitter optimized for code
    # It tries to split on double newlines, then newlines, then spaces, etc.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    
    return text_splitter.split_documents(documents)

def process_codebase(path: str) -> List[Document]:
    """Load and chunk a codebase from a given path."""
    if not os.path.exists(path):
        raise ValueError(f"Path does not exist: {path}")
        
    print(f"Loading documents from {path}...")
    raw_docs = load_documents_from_path(path)
    print(f"Loaded {len(raw_docs)} files.")
    
    print("Chunking documents...")
    chunked_docs = chunk_documents(raw_docs)
    print(f"Created {len(chunked_docs)} chunks.")
    
    return chunked_docs
