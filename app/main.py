import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from langchain_groq import ChatGroq

from app import config
from app.agent.graph import build_agent
from app.agent.tools import build_tools
from app.bot.handlers import router
from app.logging_config import setup_logging
from app.services.knowledge_base import QdrantKnowledgeBase
from app.services.web import DuckDuckGoSearcher

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging(config.LOG_LEVEL, config.LOG_FILE)
    logger.info("Launching: llm=%s embeddings=%s", config.LLM_MODEL, config.EMBEDDING_MODEL)

    logger.info("Loading knowledge base (first run downloads the embedding model)...")
    kb = QdrantKnowledgeBase(
        path=config.QDRANT_PATH,
        collection=config.COLLECTION,
        embedding_model=config.EMBEDDING_MODEL,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    llm = ChatGroq(model=config.LLM_MODEL, api_key=config.GROQ_API_KEY, temperature=0.2)

    async with httpx.AsyncClient(
        timeout=8, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
    ) as http:
        web = DuckDuckGoSearcher(http)
        tools = build_tools(kb, web, top_k=config.TOP_K)
        agent = build_agent(llm, tools, max_history=config.MAX_HISTORY)

        bot = Bot(config.BOT_TOKEN)
        dp = Dispatcher()
        dp.workflow_data.update(agent=agent, kb=kb)
        dp.include_router(router)

        logger.info("Bot is up!")
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
            logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
