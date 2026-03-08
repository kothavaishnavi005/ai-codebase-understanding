import os
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

# Path to store Chroma database locally
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")

class RAGEngine:
    def __init__(self):
        # Using completely free local embeddings via HuggingFace
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Initialize or load Chroma DB
        self.vector_store = Chroma(
            collection_name="codebase_index",
            embedding_function=self.embeddings,
            persist_directory=DB_DIR
        )
        
        # Initialize the Local LLM (Senior Engineer persona)
        # Using ultra-fast local Ollama with llama3.2:1b
        self.llm = ChatOllama(model="llama3.2:1b", temperature=0.1)
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior software engineer assistant helping developers understand a codebase.

Rules:
- Give short and clear answers.
- Limit the response to 4–5 sentences maximum.
- Use bullet points when possible.
- Focus only on the most important information.
- Avoid long explanations.
- If the user asks for more details, then provide a deeper explanation.

Your goal is to provide quick and concise explanations like a busy senior engineer.

Context:
{context}"""),
            ("human", "{question}")
        ])
        
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 3}  # Limit retrieved documents to top 3 results
        )
        
        # Construct the RAG chain
        self.chain = (
            RunnableParallel({"context": self.retriever | self._format_docs, "question": RunnablePassthrough()})
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _format_docs(self, docs) -> str:
        """Format retrieved documents into a single string with context."""
        formatted_docs = []
        for doc in docs:
            source = doc.metadata.get("source", "Unknown file")
            content = doc.page_content
            formatted_docs.append(f"--- File: {source} ---\n{content}\n")
        return "\n".join(formatted_docs)

    def add_documents(self, documents: List[Any]) -> int:
        """Add chunked documents to the vector store."""
        # Chroma will automatically persist when items are added if persist_directory is set
        self.vector_store.add_documents(documents)
        return len(documents)
        
    def query(self, question: str) -> str:
        """Query the codebase index using the RAG chain."""
        return self.chain.invoke(question)
        
    def stream(self, question: str):
        """Stream the codebase index response using the RAG chain."""
        return self.chain.stream(question)
        
    def clear_database(self):
        """Clear the existing vector database collection."""
        try:
            self.vector_store.delete_collection()
        except:
            pass
            
        # Re-initialize
        self.vector_store = Chroma(
            collection_name="codebase_index",
            embedding_function=self.embeddings,
            persist_directory=DB_DIR
        )
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 3} # Optimized context window
        )
        self.chain = (
            RunnableParallel({"context": self.retriever | self._format_docs, "question": RunnablePassthrough()})
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current vector database."""
        try:
            # Chroma collections have an access pattern to get count
            count = self.vector_store._collection.count()
            return {"status": "ok", "document_chunks": count}
        except Exception as e:
            return {"status": "error", "message": str(e), "document_chunks": 0}

# Global instance for use by API routes
_engine_instance = None

def get_rag_engine() -> RAGEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine()
    return _engine_instance
