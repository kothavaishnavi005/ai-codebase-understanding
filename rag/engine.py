import os
import logging
from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate


# ============================================================
# LOGGER SETUP
# ============================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# ============================================================
# DATABASE PATH
# ============================================================

DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "db"
)


# ============================================================
# RAG ENGINE
# ============================================================

class RAGEngine:

    def __init__(self):

        # ----------------------------------------------------
        # HuggingFace Embeddings
        # ----------------------------------------------------

        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        # ----------------------------------------------------
        # Chroma Vector Database
        # ----------------------------------------------------

        self.vector_store = Chroma(
            collection_name="codebase_index",
            embedding_function=self.embeddings,
            persist_directory=DB_DIR
        )

        # ----------------------------------------------------
        # Local Ollama LLM (Replaced with Gemini)
        # ----------------------------------------------------

        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is missing.")
            raise ValueError("Configuration Error: GEMINI_API_KEY is not set. Please set it in .env or your environment variables.")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.1,
            google_api_key=api_key
        )

        # ----------------------------------------------------
        # Main RAG Prompt
        # ----------------------------------------------------

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a senior software engineer assistant helping developers understand a codebase.

Rules:
- Give short and clear answers.
- Limit the response to 4–5 sentences maximum unless explaining code or architecture.
- YOU MUST use markdown headings and bullet points.
- Break down explanations into clear, concise sections.
- Focus only on the most important information.
- Do not write large walls of text.
- If the user asks "Where is...", explicitly list the file paths from the context and explain the exact location/logic.
- If the user asks for more details, then provide a deeper explanation.
- Use ONLY the provided context when answering questions about the codebase.
- Do not invent files, functions, features, or implementation details that are not present in the context.

Your goal is to provide quick and concise explanations like a busy senior engineer.

Context:
{context}
"""
            ),
            (
                "human",
                "{question}"
            )
        ])

        # ----------------------------------------------------
        # Code Explanation Prompt
        # ----------------------------------------------------

        self.code_explain_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a senior software engineer assistant.

The user has provided a code snippet. Analyze the code and provide a detailed explanation.

Follow these steps:

1. Explain the overall purpose of the code.
2. Describe each function and the logic steps.
3. Explain important dependencies or components.
4. Suggest improvements or best practices if possible.

Format your response cleanly using markdown.
"""
            ),
            (
                "human",
                "Code to explain:\n\n```\n{code}\n```"
            )
        ])

        # ----------------------------------------------------
        # Retriever
        # ----------------------------------------------------

        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 5,
                "fetch_k": 20
            }
        )

        logger.info("RAG Engine Initialized Successfully.")

    # ========================================================
    # CASUAL QUERY DETECTION
    # ========================================================

    def _is_casual_query(self, question: str) -> bool:
        """
        Detect simple greetings and conversational messages.

        These queries should NOT be sent to the RAG database.
        """

        normalized = question.lower().strip()

        casual_queries = {
            "hi",
            "hii",
            "hiii",
            "hello",
            "hey",
            "heyy",
            "good morning",
            "good afternoon",
            "good evening",
            "thanks",
            "thank you",
            "bye",
            "goodbye"
        }

        return normalized in casual_queries

    # ========================================================
    # CASUAL RESPONSE
    # ========================================================

    def _get_casual_response(self, question: str) -> str:
        """
        Return a simple response for casual messages.
        """

        normalized = question.lower().strip()

        casual_responses = {
            "hi": "Hi! 👋 How can I help you with the project?",
            "hii": "Hi! 👋 How can I help you with the project?",
            "hiii": "Hello! 👋 How can I help you with the project?",
            "hello": "Hello! 👋 How can I help you with the project?",
            "hey": "Hey! 👋 How can I help you with the project?",
            "heyy": "Hey! 👋 How can I help you with the project?",
            "good morning": "Good morning! ☀️ How can I help you with the project?",
            "good afternoon": "Good afternoon! 👋 How can I help you with the project?",
            "good evening": "Good evening! 👋 How can I help you with the project?",
            "thanks": "You're welcome! 😊",
            "thank you": "You're welcome! 😊",
            "bye": "Goodbye! 👋",
            "goodbye": "Goodbye! 👋"
        }

        return casual_responses.get(
            normalized,
            "Hi! 👋 How can I help you with the project?"
        )

    # ========================================================
    # FORMAT DOCUMENTS
    # ========================================================

    def _format_docs(self, docs) -> str:
        """Format retrieved documents into a single context string."""

        formatted_docs = []

        for doc in docs:
            source = doc.metadata.get(
                "source",
                "Unknown file"
            )

            content = doc.page_content

            formatted_docs.append(
                f"--- File: {source} ---\n{content}\n"
            )

        return "\n".join(formatted_docs)

    # ========================================================
    # GET UNIQUE SOURCES
    # ========================================================

    def _get_unique_sources(self, docs) -> List[str]:

        sources = []

        for doc in docs:

            src = doc.metadata.get(
                "source",
                "Unknown file"
            )

            if src not in sources:
                sources.append(src)

        return sources

    # ========================================================
    # FORMAT SOURCES
    # ========================================================

    def _format_sources(self, sources: List[str]) -> str:

        if not sources:
            return ""

        result = "\n\n**Sources:**\n"

        for src in sources:
            result += f"- `{src}`\n"

        return result

    # ========================================================
    # ADD DOCUMENTS
    # ========================================================

    def add_documents(self, documents: List[Any]) -> int:
        """Add chunked documents to the vector store."""

        try:

            self.vector_store.add_documents(
                documents
            )

            logger.info(
                f"Added {len(documents)} chunks to the vector database."
            )

            return len(documents)

        except Exception as e:

            logger.error(
                f"Failed to add documents to database: {str(e)}",
                exc_info=True
            )

            raise e

    # ========================================================
    # MAIN QUERY
    # ========================================================

    def query(self, question: str) -> str:
        """
        Query the codebase using RAG.

        Casual messages are handled directly without
        performing vector database retrieval.
        """

        logger.info(
            f"Executing query: '{question}'"
        )

        try:

            # ------------------------------------------------
            # STEP 1: Check for casual conversation
            # ------------------------------------------------

            if self._is_casual_query(question):

                logger.info(
                    "Casual query detected. Skipping RAG retrieval."
                )

                return self._get_casual_response(question)

            # ------------------------------------------------
            # STEP 2: Retrieve relevant documents
            # ------------------------------------------------

            docs = self.retriever.invoke(
                question
            )

            logger.info(
                f"Retrieved {len(docs)} documents for query."
            )

            # ------------------------------------------------
            # STEP 3: Format retrieved context
            # ------------------------------------------------

            context = self._format_docs(
                docs
            )

            # ------------------------------------------------
            # STEP 4: Create prompt
            # ------------------------------------------------

            prompt_value = self.prompt.invoke(
                {
                    "context": context,
                    "question": question
                }
            )

            # ------------------------------------------------
            # STEP 5: Send to Ollama
            # ------------------------------------------------

            answer = self.llm.invoke(
                prompt_value
            )

            # ------------------------------------------------
            # STEP 6: Get source files
            # ------------------------------------------------

            sources = self._get_unique_sources(
                docs
            )

            logger.info(
                "Query successful."
            )

            # ------------------------------------------------
            # STEP 7: Return answer + sources
            # ------------------------------------------------

            return (
                answer.content
                + self._format_sources(sources)
            )

        except Exception as e:

            logger.error(
                f"Error executing query: {str(e)}",
                exc_info=True
            )

            raise e

    # ========================================================
    # STREAM QUERY
    # ========================================================

    def stream(self, question: str):
        """
        Stream the RAG response.

        Casual queries are returned directly without
        database retrieval.
        """

        logger.info(
            f"Executing stream query: '{question}'"
        )

        try:

            # ------------------------------------------------
            # Casual query
            # ------------------------------------------------

            if self._is_casual_query(question):

                logger.info(
                    "Casual stream query detected. Skipping RAG."
                )

                yield self._get_casual_response(
                    question
                )

                return

            # ------------------------------------------------
            # Retrieve documents
            # ------------------------------------------------

            docs = self.retriever.invoke(
                question
            )

            logger.info(
                f"Retrieved {len(docs)} documents for stream query."
            )

            # ------------------------------------------------
            # Format context
            # ------------------------------------------------

            context = self._format_docs(
                docs
            )

            # ------------------------------------------------
            # Create prompt
            # ------------------------------------------------

            prompt_value = self.prompt.invoke(
                {
                    "context": context,
                    "question": question
                }
            )

            # ------------------------------------------------
            # Stream LLM response
            # ------------------------------------------------

            for chunk in self.llm.stream(
                prompt_value
            ):

                if chunk.content:
                    yield chunk.content

            # ------------------------------------------------
            # Add sources
            # ------------------------------------------------

            sources = self._get_unique_sources(
                docs
            )

            yield self._format_sources(
                sources
            )

            logger.info(
                "Stream query completed."
            )

        except Exception as e:

            logger.error(
                f"Error executing stream query: {str(e)}",
                exc_info=True
            )

            yield (
                f"\n\n**Error during streaming:** {str(e)}"
            )

    # ========================================================
    # EXPLAIN CODE
    # ========================================================

    def explain_code(self, code: str) -> str:
        """
        Explain a specific code snippet without
        using codebase retrieval.
        """

        logger.info(
            "Executing explain_code snippet."
        )

        try:

            prompt_value = self.code_explain_prompt.invoke(
                {
                    "code": code
                }
            )

            answer = self.llm.invoke(
                prompt_value
            )

            return answer.content

        except Exception as e:

            logger.error(
                f"Error in explain_code: {str(e)}",
                exc_info=True
            )

            raise e

    # ========================================================
    # STREAM CODE EXPLANATION
    # ========================================================

    def stream_explain_code(self, code: str):
        """
        Stream explanation of a specific code snippet.
        """

        logger.info(
            "Executing stream_explain_code snippet."
        )

        try:

            prompt_value = self.code_explain_prompt.invoke(
                {
                    "code": code
                }
            )

            for chunk in self.llm.stream(
                prompt_value
            ):

                if chunk.content:
                    yield chunk.content

        except Exception as e:

            logger.error(
                f"Error in stream_explain_code: {str(e)}",
                exc_info=True
            )

            yield (
                f"\n\n**Error in code explanation streaming:** "
                f"{str(e)}"
            )

    # ========================================================
    # CLEAR DATABASE
    # ========================================================

    def clear_database(self):
        """Clear the existing vector database collection."""

        logger.info(
            "Attempting to clear the vector database."
        )

        try:

            self.vector_store.delete_collection()

            logger.info(
                "Collection deleted successfully."
            )

        except Exception as e:

            logger.warning(
                "Could not delete collection "
                f"(it may not exist yet): {e}"
            )

        # ----------------------------------------------------
        # Re-initialize Chroma
        # ----------------------------------------------------

        try:

            self.vector_store = Chroma(
                collection_name="codebase_index",
                embedding_function=self.embeddings,
                persist_directory=DB_DIR
            )

            self.retriever = self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 5,
                    "fetch_k": 20
                }
            )

            logger.info(
                "Vector database re-initialized."
            )

        except Exception as e:

            logger.error(
                f"Failed to re-initialize vector store: {e}",
                exc_info=True
            )

            raise e

    # ========================================================
    # DATABASE STATISTICS
    # ========================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current vector database."""

        try:

            count = self.vector_store._collection.count()

            return {
                "status": "ok",
                "document_chunks": count
            }

        except Exception as e:

            return {
                "status": "error",
                "message": str(e),
                "document_chunks": 0
            }


# ============================================================
# GLOBAL ENGINE INSTANCE
# ============================================================

_engine_instance = None


def get_rag_engine() -> RAGEngine:
    """
    Return the global RAG engine instance.
    """

    global _engine_instance

    if _engine_instance is None:
        _engine_instance = RAGEngine()

    return _engine_instance