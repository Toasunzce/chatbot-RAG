"""Абстракции, от которых зависят agent и bot. Реализации лежат в services/."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Fragment:
    """Найденный фрагмент документа (без привязки к langchain)."""

    text: str
    source: str


class KnowledgeBase(ABC):
    @abstractmethod
    async def add_file(self, user_id: int, path: Path, name: str) -> int:
        """Добавляет файл в базу пользователя, возвращает число фрагментов.
        ValueError, если формат не поддерживается."""

    @abstractmethod
    async def search(self, user_id: int, query: str, k: int = 5) -> list[Fragment]:
        """Ищет только среди документов этого пользователя."""


class WebSearcher(ABC):
    @abstractmethod
    async def search(self, query: str) -> str:
        """Возвращает текст найденных страниц с указанием источников."""