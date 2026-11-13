import asyncio
from urllib.parse import parse_qs, unquote, urlparse
import logging

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.interfaces import WebSearcher

logger = logging.getLogger(__name__)

class DuckDuckGoSearcher(WebSearcher):
    """Поиск в DuckDuckGo + параллельная загрузка первых страниц. HTTP-клиент приходит снаружи."""

    def __init__(self, client: httpx.AsyncClient, max_pages: int = 3, max_chars: int = 1500):
        self._client = client
        self._max_pages = max_pages
        self._max_chars = max_chars

    async def search(self, query: str) -> str:
        response = await self._client.post("https://html.duckduckgo.com/html/", data={"q": query})
        links = _extract_links(response.text)[: self._max_pages]
        logger.info("web search status=%s links=%d", response.status_code, len(links))
        logger.debug("links: %s", links)
        texts = await asyncio.gather(*(self._fetch_text(url) for url in links))

        found = [
            f"Источник: {url}\n{text[: self._max_chars]}"
            for url, text in zip(links, texts)
            if text
        ]
        logger.info("web search extracted pages=%d/%d", len(found), len(links))
        return "\n\n".join(found) or "Ничего не найдено."

    async def _fetch_text(self, url: str) -> str | None:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("page fetch failed url=%s error=%s", url, exc)
            return None
        return await asyncio.to_thread(trafilatura.extract, response.text)


def _extract_links(html: str) -> list[str]:
    links = []
    for a in BeautifulSoup(html, "html.parser").select(".result__a"):
        href = a.get("href", "")
        if href.startswith("//"):
            href = "https:" + href
        query = parse_qs(urlparse(href).query)
        links.append(unquote(query["uddg"][0]) if "uddg" in query else href)
    return links