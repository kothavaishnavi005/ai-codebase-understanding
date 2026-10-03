import os
import logging
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

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
    logger.info(f"Starting directory traversal at: {root_path}")
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out ignored directories
        original_dirs = len(dirnames)
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if len(dirnames) < original_dirs:
            logger.debug(f"Ignored {original_dirs - len(dirnames)} directories in {dirpath}")
        
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
                    logger.warning(f"Error reading file {file_path}: {e}")
                    
    logger.info(f"Discovered {len(documents)} supported code files.")
    return documents

def chunk_documents(documents: List[Document]) -> List[Document]:
    """Chunk code documents into smaller pieces for vector storage."""
    # Using RecursiveCharacterTextSplitter optimized for code
    # We increase chunk size to 1000 so code block logic is less likely to be split in half
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split {len(documents)} documents into {len(chunks)} contextual chunks.")
    return chunks

def process_codebase(path: str) -> List[Document]:
    """Load and chunk a codebase from a given path."""
    if not os.path.exists(path):
        logger.error(f"Provided indexing path does not exist: {path}")
        raise ValueError(f"Path does not exist: {path}")
        
    logger.info(f"Loading documents from {path}...")
    try:
        raw_docs = load_documents_from_path(path)
        
        logger.info("Chunking documents...")
        chunked_docs = chunk_documents(raw_docs)
        
        return chunked_docs
    except Exception as e:
        logger.error(f"Critical error during document processing: {e}", exc_info=True)
        raise e
