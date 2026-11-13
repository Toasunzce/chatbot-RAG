import ast
import operator
import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

from app.interfaces import KnowledgeBase, WebSearcher

logger = logging.getLogger(__name__)

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _calc(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise ValueError("unsupported expression")


def build_tools(kb: KnowledgeBase, web: WebSearcher, top_k: int = 5) -> list[BaseTool]:
    @tool
    async def search_knowledge_base(query: str, config: RunnableConfig) -> str:
        """Search the user's uploaded documents. Use it first for any question
        that may relate to the user's files."""
        user_id = config["configurable"]["user_id"]
        logger.info("tool search_knowledge_base user=%s", user_id)
        logger.debug("query: %s", query)
        fragments = await kb.search(user_id, query, k=top_k)
        if not fragments:
            return "В базе знаний ничего не найдено."
        return "\n\n".join(f"[{f.source}]\n{f.text}" for f in fragments)

    @tool
    async def web_search(query: str) -> str:
        """Search the internet for fresh information: news, prices, current events."""
        logger.info("tool web_search")
        logger.debug("query: %s", query)
        try:
            return await web.search(query)
        except Exception as exc:
            logger.warning("web_search failed: %s", exc)
            return f"Веб-поиск недоступен: {exc}"

    @tool
    def calculator(expression: str) -> str:
        """Evaluate an arithmetic expression, e.g. '(15 + 27) * 3 / 4'. Supports + - * / ** %."""
        logger.info("tool calculator")
        logger.debug("expression: %s", expression)
        try:
            return str(_calc(ast.parse(expression, mode="eval").body))
        except Exception:
            logger.warning("calculator failed to evaluate expression")
            return "Ошибка: не удалось вычислить выражение."
    return [search_knowledge_base, web_search, calculator]