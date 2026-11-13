import asyncio
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.interfaces import Fragment, KnowledgeBase


class QdrantKnowledgeBase(KnowledgeBase):
    """RAG-хранилище на Qdrant. Документы привязаны к user_id."""

    def __init__(
        self,
        *,
        path: str,
        collection: str,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        client = QdrantClient(path=path)
        if not client.collection_exists(collection):
            client.create_collection(
                collection,
                vectors_config=qm.VectorParams(
                    size=len(embeddings.embed_query("test")), distance=qm.Distance.COSINE
                ),
            )
        self._store = QdrantVectorStore(
            client=client, collection_name=collection, embedding=embeddings
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    async def add_file(self, user_id: int, path: Path, name: str) -> int:
        chunks = await asyncio.to_thread(self._load_and_split, user_id, path, name)
        await asyncio.to_thread(self._store.add_documents, chunks)
        return len(chunks)

    async def search(self, user_id: int, query: str, k: int = 5) -> list[Fragment]:
        only_user = qm.Filter(
            must=[qm.FieldCondition(key="metadata.user_id", match=qm.MatchValue(value=user_id))]
        )
        docs = await asyncio.to_thread(
            self._store.similarity_search, query, k=k, filter=only_user
        )
        return [Fragment(text=d.page_content, source=d.metadata["source"]) for d in docs]

    def _load_and_split(self, user_id: int, path: Path, name: str) -> list:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            loader = TextLoader(str(path), encoding="utf-8")
        elif suffix == ".pdf":
            loader = PyPDFLoader(str(path))
        else:
            raise ValueError(f"Unsupported format: {suffix}")

        chunks = self._splitter.split_documents(loader.load())
        for chunk in chunks:
            chunk.metadata = {"user_id": user_id, "source": name}
        return chunks