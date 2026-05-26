"""
Langchain and RAG integration for VayuAPI
"""

from typing import Any, Dict, List, Optional
from enum import Enum


class EmbeddingProvider(Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    SENTENCE_TRANSFORMERS = "sentence-transformers"


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"


class LangchainIntegration:
    """
    Langchain integration for VayuAPI.

    Simplifies working with LLMs, embeddings, and chains.

    Example:
        ```python
        from vayuapi.ai import LangchainIntegration

        lc = LangchainIntegration(
            llm_provider="openai",
            model="gpt-4"
        )

        @app.post("/chat")
        async def chat(message: str):
            response = await lc.chat(message)
            return {"response": response}
        ```
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        model: str = "gpt-3.5-turbo",
        api_key: str = None,
        temperature: float = 0.7,
        **kwargs
    ):
        self.llm_provider = llm_provider
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.llm = None
        self._initialize_llm(**kwargs)

    def _initialize_llm(self, **kwargs):
        """Initialize LLM instance."""
        try:
            if self.llm_provider == "openai":
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=self.temperature,
                    **kwargs
                )
            elif self.llm_provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=self.temperature,
                    **kwargs
                )
        except ImportError:
            print(f"Warning: {self.llm_provider} provider not installed")

    async def chat(self, message: str, context: str = None) -> str:
        """
        Send chat message to LLM.

        Args:
            message: User message
            context: Optional context

        Returns:
            LLM response
        """
        if not self.llm:
            return "LLM not configured"

        try:
            if context:
                full_message = f"Context: {context}\n\nQuestion: {message}"
            else:
                full_message = message

            response = await self.llm.ainvoke(full_message)
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"

    def create_chain(self, prompt_template: str):
        """
        Create Langchain chain.

        Args:
            prompt_template: Prompt template string

        Returns:
            Chain instance
        """
        try:
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain

            prompt = PromptTemplate.from_template(prompt_template)
            chain = LLMChain(llm=self.llm, prompt=prompt)
            return chain
        except ImportError:
            return None


class RAGPipeline:
    """
    RAG (Retrieval Augmented Generation) pipeline.

    Combines vector database search with LLM generation.

    Example:
        ```python
        from vayuapi.ai import RAGPipeline

        rag = RAGPipeline(
            vector_db="chromadb",
            embeddings="openai",
            llm="gpt-4",
            collection_name="documents"
        )

        # Add documents
        await rag.add_documents([
            "Python is a programming language",
            "FastAPI is a web framework",
            "VayuAPI is faster than FastAPI"
        ])

        # Query
        @app.post("/query")
        async def query(question: str):
            answer = await rag.query(question)
            return {"answer": answer}
        ```
    """

    def __init__(
        self,
        vector_db: str = "chromadb",
        embeddings: str = "openai",
        llm: str = "gpt-3.5-turbo",
        collection_name: str = "documents",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = 5,
        **kwargs
    ):
        self.vector_db_type = vector_db
        self.embeddings_type = embeddings
        self.llm_model = llm
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        self.vector_db = None
        self.embeddings = None
        self.llm = None
        self.retriever = None

        self._initialize(**kwargs)

    def _initialize(self, **kwargs):
        """Initialize RAG components."""
        # Initialize embeddings
        self._init_embeddings(kwargs.get("embedding_api_key"))

        # Initialize vector database
        self._init_vector_db(kwargs)

        # Initialize LLM
        self._init_llm(kwargs.get("llm_api_key"))

    def _init_embeddings(self, api_key: str = None):
        """Initialize embeddings model."""
        try:
            if self.embeddings_type == "openai":
                from langchain_openai import OpenAIEmbeddings
                self.embeddings = OpenAIEmbeddings(api_key=api_key)
            elif self.embeddings_type == "huggingface":
                from langchain_huggingface import HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings()
        except ImportError:
            print(f"Warning: Embeddings provider {self.embeddings_type} not installed")

    def _init_vector_db(self, config: Dict):
        """Initialize vector database."""
        try:
            if self.vector_db_type == "chromadb":
                from langchain_chroma import Chroma
                self.vector_db = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings
                )
            elif self.vector_db_type == "pinecone":
                from langchain_pinecone import PineconeVectorStore
                self.vector_db = PineconeVectorStore(
                    index_name=self.collection_name,
                    embedding=self.embeddings
                )
        except ImportError:
            print(f"Warning: Vector DB {self.vector_db_type} not installed")

    def _init_llm(self, api_key: str = None):
        """Initialize LLM."""
        try:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=self.llm_model,
                api_key=api_key,
                temperature=0.7
            )
        except ImportError:
            print("Warning: LLM provider not installed")

    async def add_documents(
        self,
        documents: List[str],
        metadata: List[Dict] = None
    ):
        """
        Add documents to vector database.

        Args:
            documents: List of document strings
            metadata: Optional metadata for each document
        """
        if not self.vector_db:
            return

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )

            docs = [
                Document(page_content=doc, metadata=meta or {})
                for doc, meta in zip(documents, metadata or [{}] * len(documents))
            ]

            splits = text_splitter.split_documents(docs)

            # Add to vector database
            await self.vector_db.aadd_documents(splits)
        except Exception as e:
            print(f"Error adding documents: {e}")

    async def query(
        self,
        question: str,
        return_sources: bool = False
    ) -> str:
        """
        Query the RAG pipeline.

        Args:
            question: User question
            return_sources: Whether to return source documents

        Returns:
            Generated answer
        """
        if not self.vector_db or not self.llm:
            return "RAG pipeline not configured"

        try:
            # Retrieve relevant documents
            docs = await self.vector_db.asimilarity_search(question, k=self.top_k)

            # Build context from retrieved documents
            context = "\n\n".join([doc.page_content for doc in docs])

            # Generate answer using LLM
            prompt = f"""Based on the following context, answer the question.
            
Context:
{context}

Question: {question}

Answer:"""

            response = await self.llm.ainvoke(prompt)
            answer = response.content

            if return_sources:
                sources = [{"content": doc.page_content, "metadata": doc.metadata}
                          for doc in docs]
                return {"answer": answer, "sources": sources}

            return answer
        except Exception as e:
            return f"Error querying RAG: {str(e)}"

    async def clear_documents(self):
        """Clear all documents from vector database."""
        if self.vector_db:
            try:
                await self.vector_db.adelete_collection()
            except:
                pass
