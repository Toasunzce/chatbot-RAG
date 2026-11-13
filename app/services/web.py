import asyncio
from urllib.parse import parse_qs, unquote, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.interfaces import WebSearcher


class DuckDuckGoSearcher(WebSearcher):
    """Поиск в DuckDuckGo + параллельная загрузка первых страниц. HTTP-клиент приходит снаружи."""

    def __init__(self, client: httpx.AsyncClient, max_pages: int = 3, max_chars: int = 1500):
        self._client = client
        self._max_pages = max_pages
        self._max_chars = max_chars

    async def search(self, query: str) -> str:
        response = await self._client.post("https://html.duckduckgo.com/html/", data={"q": query})
        links = _extract_links(response.text)[: self._max_pages]
        texts = await asyncio.gather(*(self._fetch_text(url) for url in links))

        found = [
            f"Source: {url}\n{text[: self._max_chars]}"
            for url, text in zip(links, texts)
            if text
        ]
        return "\n\n".join(found) or "Nothing found."

    async def _fetch_text(self, url: str) -> str | None:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
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